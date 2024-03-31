import datetime
import time
from threading import Thread

import pyaudio
import wave
from loguru import logger

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 1)  # 1000ms
CHANNEL = 1
SAMPLE_WIDTH = pyaudio.paInt16
RECORDING_CHUNK_SIZE = 120
FILE_EXTENSION = 'wav'
CHUNK_DIR = 'audio/'


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self: object, rate: int = RATE, chunk: int = CHUNK) -> None:
        """The audio -- and generator -- is guaranteed to be on the main thread."""
        self._rate = rate
        self._chunk = chunk
        self._channel = CHANNEL
        self._sample_width = SAMPLE_WIDTH

        self._audio_interface = None
        self._audio_stream = None

        self._recording_frames = []
        self._count = 0
        self._session_id = datetime.datetime.now().strftime('%y%m%d%H%M%S')

    def start_recording(self: object) -> None:
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=self._sample_width,
            channels=self._channel,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )

    def stop_recording(self: object) -> None:
        """Closes the stream, regardless of whether the connection was lost or not."""
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self._audio_interface.terminate()

        if self._recording_frames:
            saving_frames = self._recording_frames[:]
            self._recording_frames = []
            self._count += 1

            self._create_chunk_saving_thread(saving_frames, self._count)

        logger.info('Microphone has been closed')

    def _fill_buffer(
        self: object,
        in_data: object,
        frame_count: int,
        time_info: object,
        status_flags: object,
    ) -> object:
        """Continuously collect data from the audio stream, into the buffer.

        Args:
            in_data: The audio data as a bytes object
            frame_count: The number of frames captured
            time_info: The time information
            status_flags: The status flags

        Returns:
            The audio data as a bytes object
        """
        logger.info(f'fill buffer: {len(self._recording_frames)}')
        self._recording_frames.append(in_data)
        if len(self._recording_frames) >= RECORDING_CHUNK_SIZE:
            saving_frames = self._recording_frames[:]
            self._recording_frames = []
            self._count += 1

            # FIXME
            self._create_chunk_saving_thread(saving_frames, self._count)

        return None, pyaudio.paContinue

    def _create_chunk_saving_thread(self, saving_frames, count):
        created_at = datetime.datetime.now().strftime('%y%m%d%H%M%S')

        saving_thread = Thread(
            target=self._save,
            args=(saving_frames, count, created_at,),
            daemon=True,
        )
        saving_thread.start()
        logger.info(f'Start saving: session_id: {self._session_id}, count: {self._count}')


    def _save(self, frames, count, start_time):
        with wave.open(f'{CHUNK_DIR}{self._session_id}_{count:02}.{FILE_EXTENSION}', 'wb') as wf:
            wf.setnchannels(self._channel)
            wf.setsampwidth(self._audio_interface.get_sample_size(self._sample_width))
            wf.setframerate(self._rate)
            wf.writeframes(b''.join(frames))
        logger.info(f'Finish recording: count: {count}, start_time: {start_time}, frames: {len(frames)}')


def main() -> None:
    try:
        stream = MicrophoneStream()
        stream.start_recording()
        time.sleep(65)
        stream.stop_recording()
    except KeyboardInterrupt:
        logger.info('Force shut down')


if __name__ == "__main__":
    main()
