import io
import soundfile as sf
import pyaudio
import wave
import RPi.GPIO as GPIO
import threading
from queue import Queue
import time
from faster_whisper import WhisperModel
import asyncio

model_size = "tiny.en"
form_1 = pyaudio.paInt16 # 16-bit resolution
chans = 1
samp_rate = 16000
chunk = 1024 # 2^12 samples for buffer
record_secs = 3 # seconds to record
dev_index = 1 # device index found by p.get_device_info_by_index(ii)


# Set up GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

model = WhisperModel(model_size, device="cpu", compute_type="int8")
print('done loading')

def record_audio(stream, queue):
    # loop through stream and append audio chunks to frame array

    for i in range(20):
        frames = []
        for ii in range(0, int((samp_rate / chunk) * record_secs)):
            data = stream.read(chunk)
            frames.append(data)
        queue.put(b''.join(frames))


def transcribe_frame(model, frame):
    segments, info = model.transcribe(
        frame, beam_size=2, language="en", condition_on_previous_text=True
    )
    # import pdb;pdb.set_trace()
    for segment in segments:
        print(segment.text, end=" ", flush=True)
        text = True


def create_in_memory_wav(audio, audio_frame):
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(chans)  # Number of channels
        wf.setsampwidth(audio.get_sample_size(form_1))  # Sample width from PyAudio format
        wf.setframerate(samp_rate)  # Sample rate
        wf.writeframes(audio_frame)

    wav_io.seek(0)
    return wav_io

def second_pass_thread(model, audio, audio_frames, window_size):
    while True:
        if len(audio_frames) >= window_size:
            frames_to_process = b''.join(audio_frames[:window_size])
            audio_frames = audio_frames[window_size:]

            wav_io = create_in_memory_wav(audio, frames_to_process)

            segments, info = model.transcribe(
                wav_io, beam_size=2, language="en", condition_on_previous_text=True
            )

            for segment in segments:
                print(f"\nSecond Pass: {segment.text}", flush=True)

            time.sleep(0.1)  # Add a small delay to avoid excessive CPU usage

        time.sleep(0.1)  # Add a small delay to avoid excessive CPU usage

def worker(queue, audio, audio_frames):
    counter = 0
    while True:

        # if counter == 4:
        #     import pdb; pdb.set_trace()
        # counter +=1

        frame = queue.get()
        if frame is None:
            break

        wav_io = create_in_memory_wav(audio, frame)
        transcribe_frame(model, wav_io)

        audio_frames.append(frame)

        queue.task_done()
        time.sleep(0.1)  # Add a small delay to avoid excessive CPU usage



def button_pressed_callback(channel):
    print("Button pressed!")

    audio = pyaudio.PyAudio()
    stream = audio.open(format=form_1, rate=samp_rate, channels=chans,
                        input_device_index=dev_index, input=True,
                        frames_per_buffer=chunk)

    frame_queue = Queue()
    audio_frames = []

    num_workers = 1
    for _ in range(num_workers):
        threading.Thread(target=worker, args=(frame_queue, audio, audio_frames), daemon=True).start()

    second_pass_thread_handle = threading.Thread(target=second_pass_thread, args=(model, audio, audio_frames, 3), daemon=True)
    second_pass_thread_handle.start()

    print("Recording and transcribing...")
    record_audio(stream, frame_queue)

    frame_queue.join()

    for _ in range(num_workers):
        frame_queue.put(None)

    print("Finished recording and transcribing.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # save the audio frames as .wav file

# Add event detection and callback function
GPIO.add_event_detect(23, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)


try:
    # Keep the script running
    while True:
        time.sleep(3)

except KeyboardInterrupt:
    # Clean up GPIO and exit
    GPIO.cleanup()




