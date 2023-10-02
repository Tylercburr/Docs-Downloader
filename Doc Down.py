from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from PIL import Image
import pickle
import os
import io
from bs4 import BeautifulSoup
import requests
import PySimpleGUI as sg

sg.theme('SandyBeach')

layout = [
    [sg.Text('Please enter the save path and the file_id')],
    [sg.Text('Save Path', size=(15, 1)), sg.InputText()],
    [sg.Text('File ID', size=(15, 1)), sg.InputText()],
    [sg.Submit(), sg.Cancel()]
]

window = sg.Window('Simple data entry window', layout)
event, values = window.read()
window.close()

save_path = values[0]


SCOPES = ['https://www.googleapis.com/auth/drive']

creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        if os.path.getsize('token.pickle') > 0:  # Check if file is not empty
            creds = pickle.load(token)
        else:
            creds = None

# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('drive', 'v3', credentials=creds)

file_id = values[1]
request = service.files().export_media(fileId=file_id, mimeType='text/html')
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)
done = False
while done is False:
    status, done = downloader.next_chunk()

html_content = fh.getvalue().decode()
soup = BeautifulSoup(html_content, 'html.parser')

for img in soup.find_all('img'):
    img_url = img['src']
    img_data = requests.get(img_url).content
    img_name = os.path.basename(img_url)
    
    # Open the raw image data as an image object
    img_object = Image.open(io.BytesIO(img_data))
    
    # Save the image object to a file
    img_object.save(os.path.join('Keeps/' + save_path, img_name + '.' + img_object.format))


