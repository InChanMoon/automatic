"""
Google Drive 이미지 관리자

배치 폴더 시스템을 통한 이미지 관리
"""

import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build


class DriveImageManager:
    """Google Drive 이미지 관리 클래스"""

    def __init__(self, config_path="config.json", credentials_path="credentials/google_service_account.json"):
        """
        초기화

        Args:
            config_path: config.json 경로
            credentials_path: Service Account JSON 경로
        """
        # Config 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.root_folder_id = self.config['google_drive']['root_folder_id']
        self.move_to_used = self.config['google_drive']['move_to_used']

        # Drive API 연결
        SCOPES = [
            'https://www.googleapis.com/auth/drive'
        ]

        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )

        self.service = build('drive', 'v3', credentials=creds)

    def find_keyword_folder(self, keyword):
        """
        키워드 폴더 찾기

        Args:
            keyword: 키워드

        Returns:
            str: 폴더 ID 또는 None
        """
        query = f"name='{keyword}' and mimeType='application/vnd.google-apps.folder' and '{self.root_folder_id}' in parents"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=10
        ).execute()

        files = results.get('files', [])

        if files:
            return files[0]['id']

        return None

    def get_batch_folders(self, keyword_folder_id):
        """
        배치 폴더 목록 가져오기 (001, 002, ...)

        Args:
            keyword_folder_id: 키워드 폴더 ID

        Returns:
            list: [{'id': ..., 'name': '001'}, {'id': ..., 'name': '002'}, ...]
                  이름 순으로 정렬됨
        """
        query = f"mimeType='application/vnd.google-apps.folder' and '{keyword_folder_id}' in parents"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=100
        ).execute()

        folders = results.get('files', [])

        # 숫자 폴더만 필터링 (001, 002 등)
        batch_folders = []
        for folder in folders:
            if folder['name'].isdigit():
                batch_folders.append(folder)

        # 이름 기준 정렬
        batch_folders.sort(key=lambda x: x['name'])

        return batch_folders

    def get_images_from_batch(self, batch_folder_id):
        """
        배치 폴더에서 이미지 파일 목록 가져오기

        Args:
            batch_folder_id: 배치 폴더 ID

        Returns:
            list: [{'id': ..., 'name': 'image.jpg', 'webContentLink': ...}, ...]
        """
        query = f"'{batch_folder_id}' in parents and (mimeType contains 'image/')"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, webContentLink, webViewLink)',
            pageSize=100
        ).execute()

        return results.get('files', [])

    def download_image(self, file_id, save_path):
        """
        이미지 다운로드

        Args:
            file_id: 파일 ID
            save_path: 저장 경로
        """
        request = self.service.files().get_media(fileId=file_id)

        with open(save_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

    def get_next_batch(self, keyword):
        """
        다음 사용할 배치 폴더 가져오기

        Args:
            keyword: 키워드

        Returns:
            dict: {
                'batch_folder_id': str,
                'batch_name': str,
                'images': [...]
            } 또는 None
        """
        # 1. 키워드 폴더 찾기
        keyword_folder_id = self.find_keyword_folder(keyword)

        if not keyword_folder_id:
            print(f"❌ 키워드 폴더를 찾을 수 없습니다: {keyword}")
            return None

        # 2. 배치 폴더 목록 가져오기
        batch_folders = self.get_batch_folders(keyword_folder_id)

        if not batch_folders:
            print(f"❌ 배치 폴더가 없습니다: {keyword}")
            return None

        # 3. 첫 번째 배치 선택
        first_batch = batch_folders[0]

        # 4. 이미지 목록 가져오기
        images = self.get_images_from_batch(first_batch['id'])

        return {
            'batch_folder_id': first_batch['id'],
            'batch_name': first_batch['name'],
            'keyword_folder_id': keyword_folder_id,
            'images': images
        }

    def move_batch_to_used(self, batch_folder_id, keyword_folder_id):
        """
        배치 폴더를 _used 폴더로 이동

        Args:
            batch_folder_id: 배치 폴더 ID
            keyword_folder_id: 키워드 폴더 ID
        """
        if not self.move_to_used:
            return

        # _used 폴더 찾기 또는 생성
        used_folder_id = self.find_or_create_used_folder(keyword_folder_id)

        # 배치 폴더 이동
        self.service.files().update(
            fileId=batch_folder_id,
            addParents=used_folder_id,
            removeParents=keyword_folder_id,
            fields='id, parents'
        ).execute()

        print(f"✅ 배치 폴더를 _used로 이동 완료")

    def find_or_create_used_folder(self, keyword_folder_id):
        """
        _used 폴더 찾기 또는 생성

        Args:
            keyword_folder_id: 키워드 폴더 ID

        Returns:
            str: _used 폴더 ID
        """
        query = f"name='_used' and mimeType='application/vnd.google-apps.folder' and '{keyword_folder_id}' in parents"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=10
        ).execute()

        files = results.get('files', [])

        if files:
            return files[0]['id']

        # 없으면 생성
        file_metadata = {
            'name': '_used',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [keyword_folder_id]
        }

        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        print(f"✅ _used 폴더 생성 완료")

        return folder.get('id')


# 이미지 다운로드를 위한 import (필요 시)
try:
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    pass
