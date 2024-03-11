import time
import random
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from PIL import Image, ImageFile
import pickle
import os
import io
from bs4 import BeautifulSoup
import requests
import PySimpleGUI as sg
import base64


def create_album(photos_service, album_title):
    print(f"Start create_album with photo_service: {photos_service} album_title: {photos_service}")
    # List all albums
    albums_list = photos_service.albums().list().execute()
    print(f"albums_list: {albums_list}")

    # Check if album already exists
    for album in albums_list.get('albums', []):
        if album.get('title') == album_title:
            return album  # Return the existing album

    # If album does not exist, create a new one
    create_album_body = {
        'album': {'title': album_title}
    }
    return photos_service.albums().create(body=create_album_body).execute()

def upload_image(image_path):
    # Read the image file in binary mode
    with open(image_path, 'rb') as photo_file:
        binary_photo_data = photo_file.read()

    # Convert the binary data to base64
    base64_photo_data = base64.b64encode(binary_photo_data).decode('utf-8')

    # Create the headers for the upload request
    headers = {
        'Authorization': 'Bearer ' + creds.token,
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-Protocol': 'raw',
        'X-Goog-Upload-File-Name': os.path.basename(image_path),
    }

    # Make the POST request to upload the image and get the upload token
    upload_response = requests.post(
        'https://photoslibrary.googleapis.com/v1/uploads',
        headers=headers,
        data=base64_photo_data
    )

    # Check if the upload was successful
    if upload_response.status_code == 200:
        upload_token = upload_response.text
        if upload_token:
            return upload_token
        else:
            print(f"Upload succeeded but no upload token received for image: {image_path}")
            return None
    else:
        print(f"Upload failed with status code: {upload_response.status_code} for image: {image_path}")
        return None
    

def batch_upload_images(photos_service, album_id, image_paths):
    new_media_items = []

    for i in range(0, len(image_paths), 30):
        batch = image_paths[i:i+30]
        for image_path in batch:
            # Upload the image and get the upload token
            upload_token = upload_image(image_path)
            if upload_token is None:
                print(f"Failed to upload image: {image_path}")
                continue
            
            print(f"Uploaded image successfully: {image_path}")
            # print(f"Upload token: {upload_token}")  # Print the upload token

            # Add the new media item to the list
            new_media_items.append({
                'description': 'My new photo',
                'simpleMediaItem': {'uploadToken': upload_token}
            })
            print(f"New media item: {new_media_items}")

        # Create the media items in a single batch request
        file_metadata = {
            'albumId': album_id,
            'newMediaItems': new_media_items
        }
        response = photos_service.mediaItems().batchCreate(body=file_metadata).execute()
        print(f"Batch create response: {response}")  # Print the batch create response

        for result in response.get('newMediaItemResults', []):
            print(f"Media item status: {result.get('status', {}).get('message')}")

        if i + 30 < len(image_paths):
            time.sleep(60)  # Wait for 60 seconds if there are more images to upload



if __name__ == '__main__':
    sg.theme('SandyBeach')
    ImageFile.LOAD_TRUNCATED_IMAGES = True

    layout = [
        [sg.Text('Please enter the save path, the file_id, and the album name')],
        [sg.Text('Save Path', size=(15, 1)), sg.InputText()],
        [sg.Text('File ID', size=(15, 1)), sg.InputText()],
        [sg.Text('Album Name', size=(15, 1)), sg.InputText()],
        [sg.Submit(), sg.Cancel()]
    ]

    window = sg.Window('Simple data entry window', layout)
    event, values = window.read()
    window.close()

    save_path = values[0] if values[0] is not None else 'default_save_path'
    album_name = values[2]

    if not os.path.exists('Keeps/' + save_path):
        os.makedirs('Keeps/' + save_path)

    SCOPES = ['https://www.googleapis.com/auth/photoslibrary', 'https://www.googleapis.com/auth/drive']

    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            if os.path.getsize('token.pickle') > 0:
                creds = pickle.load(token)
            else:
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    drive_service = build('drive', 'v3', credentials=creds)
    photos_service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

    file_id = values[1]
    request = drive_service.files().export_media(fileId=file_id, mimeType='text/html')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    html_content = fh.getvalue().decode()
    soup = BeautifulSoup(html_content, 'html.parser')

    new_album = create_album(photos_service, album_name)
    print(f"New album: {new_album}")
    album_id = new_album['id']

    image_counter = 1
    image_paths = []
    for img in soup.find_all('img'):
        if 'src' in img.attrs:
         img_url = img['src']
         img_data = requests.get(img_url).content
         img_name = "Image" + str(image_counter)
         image_counter += 1

         img_object = Image.open(io.BytesIO(img_data))
         img_path = os.path.join('Keeps/' + save_path + '/', img_name + '.' + img_object.format)
         print(f"Saving image: {img_path}")
         img_object.save(img_path)

         image_paths.append(img_path)

         # Batch upload the images every 50 images
         if len(image_paths) >= 50:
            batch_upload_images(photos_service, album_id, image_paths)
            image_paths = []

        else:
            print(f"Image tag without 'src' atribute found: {img}")
            
    if image_paths:
        batch_upload_images(photos_service, album_id, image_paths)
