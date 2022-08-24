#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
"""
Conversation transcription samples for the Microsoft Cognitive Services Speech SDK
"""

import time
import uuid
import logging
import requests

from scipy.io import wavfile

import swagger_client as cris_client

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    print("""
    Importing the Speech SDK for Python failed.
    Refer to
    https://docs.microsoft.com/azure/cognitive-services/speech-service/quickstart-python for
    installation instructions.
    """)
    import sys
    sys.exit(1)

# Set up the subscription info for the Speech Service:
# Replace with your own subscription key and service region (e.g., "centralus").
# See the limitations in supported regions,
# https://docs.microsoft.com/azure/cognitive-services/speech-service/how-to-use-conversation-transcription
speech_key, service_region = "8199c9fb1e2c4c2db4497d76738a6ef1", "eastus"

LOCALE = "en-US"
RECORDINGS_BLOB_URI = "https://meetingassistantstore.blob.core.windows.net/containaudio/ES2008a.Mix-Headset16khz.wav?sp=r&st=2022-06-20T01:59:05Z&se=2022-06-20T09:59:05Z&spr=https&sv=2021-06-08&sr=b&sig=IRZedd4wo2%2FDzmu7xAi9GQNTCg3LwBFKt7x91dHZi08%3D"

# Provide the uri of a container with audio files for transcribing all of them with a single request
RECORDINGS_CONTAINER_URI = "https://meetingassistantstore.blob.core.windows.net/containaudio?sp=racwl&st=2022-06-19T18:56:51Z&se=2022-06-20T02:56:51Z&spr=https&sv=2021-06-08&sr=c&sig=%2B2QKmDBjSiRZPFPmCoao8udZcMIzwKVyNiP4lB6RnJI%3D"

NAME = "Simple transcription"
DESCRIPTION = "Simple transcription description"

def _paginate(api, paginated_object):
    """
    The autogenerated client does not support pagination. This function returns a generator over
    all items of the array that the paginated object `paginated_object` is part of.
    """
    yield from paginated_object.values
    typename = type(paginated_object).__name__
    auth_settings = ["apiKeyHeader", "apiKeyQuery"]
    while paginated_object.next_link:
        link = paginated_object.next_link[len(api.api_client.configuration.host):]
        paginated_object, status, headers = api.api_client.call_api(link, "GET",
            response_type=typename, auth_settings=auth_settings)

        if status == 200:
            yield from paginated_object.values
        else:
            raise Exception(f"could not receive paginated data: status {status}")

def transcribe_from_single_blob(uri, properties):
    """
    Transcribe a single audio file located at `uri` using the settings specified in `properties`
    using the base model for the specified locale.
    """
    transcription_definition = cris_client.Transcription(
        display_name=NAME,
        description=DESCRIPTION,
        locale=LOCALE,
        content_urls=[uri],
        properties=properties
    )

    return transcription_definition

properties = {
        "punctuationMode": "DictatedAndAutomatic",
        "profanityFilterMode": "Masked",
        "wordLevelTimestampsEnabled": True,
        "diarizationEnabled": True,
        "destinationContainerUrl": "", # <SAS Uri with at least write (w) permissions for an Azure Storage blob container that results should be written to>
        "timeToLive": "PT1H"
    }

logging.info("Starting transcription client...")

# configure API key authorization: subscription_key
configuration = cris_client.Configuration()
configuration.api_key["Ocp-Apim-Subscription-Key"] = speech_key
configuration.host = f"https://eastus.api.cognitive.microsoft.com/speechtotext/v3.0"

# create the client object and authenticate
client = cris_client.ApiClient(configuration)

# create an instance of the transcription api class
api = cris_client.CustomSpeechTranscriptionsApi(api_client=client)

transcription_definition = transcribe_from_single_blob(RECORDINGS_BLOB_URI, properties)

    # Uncomment this block to use custom models for transcription.
    # transcription_definition = transcribe_with_custom_model(api, RECORDINGS_BLOB_URI, properties)

    # Uncomment this block to transcribe all files from a container.
    # transcription_definition = transcribe_from_container(RECORDINGS_CONTAINER_URI, properties)

print(transcription_definition)


created_transcription, status, headers = api.create_transcription_with_http_info(transcription=transcription_definition)

# get the transcription Id from the location URI
transcription_id = headers["location"].split("/")[-1]

# Log information about the created transcription. If you should ask for support, please
# include this information.
logging.info(f"Created new transcription with id '{transcription_id}' in region {service_region}")

logging.info("Checking status.")

completed = False

while not completed:
    # wait for 5 seconds before refreshing the transcription status
    time.sleep(5)

    transcription = api.get_transcription(transcription_id)
    logging.info(f"Transcriptions status: {transcription.status}")

    if transcription.status in ("Failed", "Succeeded"):
        completed = True

    if transcription.status == "Succeeded":
        pag_files = api.get_transcription_files(transcription_id)
        for file_data in _paginate(api, pag_files):
            if file_data.kind != "Transcription":
                continue

            audiofilename = file_data.name
            results_url = file_data.links.content_url
            results = requests.get(results_url)
            logging.info(f"Results for {audiofilename}:\n{results.content.decode('utf-8')}")
    elif transcription.status == "Failed":
        logging.info(f"Transcription failed: {transcription.properties.error.message}")

# This sample uses a wavfile which is captured using a supported Speech SDK devices (8 channel, 16kHz, 16-bit PCM)
# See https://docs.microsoft.com/azure/cognitive-services/speech-service/speech-devices-sdk-microphone
conversationfilename = "xx.wav"

propertyID = speechsdk.PropertyId(3200)

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region="eastus")
speech_config.speech_recognition_language="pt-BR"
speech_config.set_property(propertyID, "1000000");
print(speech_config.get_property(propertyID))

def speech_recognize_continuous_from_file():
    done = False

    def stop_cb(evt):
            """callback that stops continuous recognition upon receiving an event `evt`"""
            print('CLOSING on {}'.format(evt))
            speech_recognizer.stop_continuous_recognition()
            nonlocal done
            done = True


    audio_config = speechsdk.AudioConfig(filename=conversationfilename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_recognizer.start_continuous_recognition()

    speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
    speech_recognizer.recognized.connect(lambda evt: print('RECOGNIZED: {}'.format(evt)))
    speech_recognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

        # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

    print(result)


# This sample demonstrates how to differentiate speakers using conversation transcription service.
# Differentiation of speakers do not require voice signatures. In case more enhanced speaker identification is required,
# please use https://signature.centralus.cts.speech.microsoft.com/UI/index.html REST API to create your own voice signatures
def conversation_transcription_differentiate_speakers():
    # Creates speech configuration with subscription information
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.set_property_by_name("ConversationTranscriptionInRoomAndOnline", "true")
    speech_config.set_property_by_name("DifferentiateGuestSpeakers", "true")

    channels = 8
    bits_per_sample = 16
    samples_per_second = 16000

    # Create audio configuration using the push stream
    wave_format = speechsdk.audio.AudioStreamFormat(samples_per_second, bits_per_sample, channels)
    stream = speechsdk.audio.PushAudioInputStream(stream_format=wave_format)
    audio_config = speechsdk.audio.AudioConfig(stream=stream)

    # Conversation identifier is required when creating conversation.
    conversation_id = str(uuid.uuid4())
    conversation = speechsdk.transcription.Conversation(speech_config, conversation_id)
    transcriber = speechsdk.transcription.ConversationTranscriber(audio_config)

    done = False

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous transcription upon receiving an event `evt`"""
        print('CLOSING {}'.format(evt))
        nonlocal done
        done = True

    # Subscribe to the events fired by the conversation transcriber
    transcriber.transcribed.connect(lambda evt: print('TRANSCRIBED: {}'.format(evt)))
    transcriber.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
    transcriber.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
    transcriber.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))
    # stop continuous transcription on either session stopped or canceled events
    transcriber.session_stopped.connect(stop_cb)
    transcriber.canceled.connect(stop_cb)
    
    '''
    # Add participants to the conversation.
    # Note user voice signatures are not required for speaker differentiation.
    # Use voice signatures when adding participants when more enhanced speaker identification is required.
    katie = speechsdk.transcription.Participant("katie@example.com", "en-us")
    stevie = speechsdk.transcription.Participant("stevie@example.com", "en-us")

    conversation.add_participant_async(katie)
    conversation.add_participant_async(stevie)
    '''    

    transcriber.join_conversation_async(conversation).get()
    transcriber.start_transcribing_async()

    # Read the whole wave files at once and stream it to sdk
    _, wav_data = wavfile.read(conversationfilename)
    stream.write(wav_data.tobytes())
    stream.close()
    while not done:
        time.sleep(.5)

    transcriber.stop_transcribing_async()

conversation_transcription_differentiate_speakers()
