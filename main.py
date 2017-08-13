

import json
import logging
import os.path

import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

from server import HttpServer
from server import SERVER_PORT
from server import SERVER_AUDIO_FILE
from server import LOCAL_AUDIO_FILE

try:
    from . import (
        assistant_helpers,
        audio_helpers,
        pushtotalk,
        sonos_helpers
    )
except ImportError:
    import assistant_helpers
    import audio_helpers
    import pushtotalk
    import sonos_helpers


def configure_conversation_stream(input_audio_file, audio_sample_rate, audio_sample_width,
                                  audio_iter_size, audio_block_size, audio_flush_size):
    if input_audio_file:
        audio_source = audio_helpers.WaveSource(
            open(input_audio_file, 'rb'),
            sample_rate=audio_sample_rate,
            sample_width=audio_sample_width
        )
    else:
        audio_source = audio_helpers.SoundDeviceStream(
                sample_rate=audio_sample_rate,
                sample_width=audio_sample_width,
                block_size=audio_block_size,
                flush_size=audio_flush_size
            )
    audio_sink = audio_helpers.WaveSink(
        open(LOCAL_AUDIO_FILE, 'wb'),
        sample_rate=audio_sample_rate,
        sample_width=audio_sample_width
    )
    return audio_helpers.ConversationStream(
        source=audio_source,
        sink=audio_sink,
        iter_size=audio_iter_size,
        sample_width=audio_sample_width,
    )


def auth(credentials):
    with open(credentials, 'r') as f:
        credentials = google.oauth2.credentials.Credentials(token=None, **json.load(f))
        http_request = google.auth.transport.requests.Request()
        credentials.refresh(http_request)
        return http_request, credentials


def sonos_out(sonos, out_uri):
    sonos.play_uri(out_uri)
    logging.info('Playing ' + out_uri + ' on sonos ' + sonos.player_name)


@click.command()
@click.option('--api-endpoint', default=pushtotalk.ASSISTANT_API_ENDPOINT,
              metavar='<api endpoint>', show_default=True,
              help='Address of Google Assistant API service.')
@click.option('--credentials',
              metavar='<credentials>', show_default=True,
              default=os.path.join(click.get_app_dir('google-oauthlib-tool'),
                                   'credentials.json'),
              help='Path to read OAuth2 credentials.')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Verbose logging.')
@click.option('--input-audio-file', '-i',
              metavar='<input file>',
              help='Path to input audio file. '
              'If missing, uses audio capture')
@click.option('--output-audio-path', '-o',
              metavar='<output path>',
              help='Path to output audio. '
              'If missing, uses audio playback')
@click.option('--audio-sample-rate',
              default=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
              metavar='<audio sample rate>', show_default=True,
              help='Audio sample rate in hertz.')
@click.option('--audio-sample-width',
              default=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
              metavar='<audio sample width>', show_default=True,
              help='Audio sample width in bytes.')
@click.option('--audio-iter-size',
              default=audio_helpers.DEFAULT_AUDIO_ITER_SIZE,
              metavar='<audio iter size>', show_default=True,
              help='Size of each read during audio stream iteration in bytes.')
@click.option('--audio-block-size',
              default=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
              metavar='<audio block size>', show_default=True,
              help=('Block size in bytes for each audio device '
                    'read and write operation..'))
@click.option('--audio-flush-size',
              default=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE,
              metavar='<audio flush size>', show_default=True,
              help=('Size of silence data in bytes written '
                    'during flush operation'))
@click.option('--grpc-deadline', default=pushtotalk.DEFAULT_GRPC_DEADLINE,
              metavar='<grpc deadline>', show_default=True,
              help='gRPC deadline in seconds')
@click.option('--once', default=False, is_flag=True,
              help='Force termination after a single conversation.')
def main(api_endpoint, credentials, verbose,
         input_audio_file, output_audio_path,
         audio_sample_rate, audio_sample_width,
         audio_iter_size, audio_block_size, audio_flush_size,
         grpc_deadline, once, *args, **kwargs):
    """
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    sonos = sonos_helpers.get_sonos()
    server = HttpServer(SERVER_PORT)
    server.start()

    try:
        http_request, credentials = auth(credentials)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, api_endpoint)
    logging.info('Connecting to %s', api_endpoint)

    conversation_stream = configure_conversation_stream(input_audio_file, audio_sample_rate,
                                                        audio_sample_width, audio_iter_size, audio_block_size,
                                                        audio_flush_size)

    with pushtotalk.SampleAssistant(conversation_stream,
                         grpc_channel, grpc_deadline) as assistant:
        wait_for_user_trigger = not once
        while True:
            if wait_for_user_trigger:
                click.pause(info='Press Enter to send a new request...')
            continue_conversation = assistant.converse()
            sonos_out(sonos, SERVER_AUDIO_FILE)
            wait_for_user_trigger = not continue_conversation
            if once and (not continue_conversation):
                break

if __name__ == '__main__':
    main()
