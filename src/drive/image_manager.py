"""
Google Drive 이미지 매니저 V2

키워드별 이미지 폴더 관리 및 로컬 캐시 처리
- 이미지 인덱스는 스프레드시트에 저장되어 영속성 보장
"""

import os
import io
import json
import hashlib
from typing import List, Dict, Optional, Callable
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class DriveImageManager:
    """Google Drive 이미지 매니저 클래스"""

    def __init__(
        self,
        config_path: str = "config.json",
        credentials_path: str = "credentials/google_service_account.json",
        cache_dir: str = "image_cache",
        settings_mgr=None,
        group_name: str = None
    ):
        """
        초기화

        Args:
            config_path: config.json 경로
            credentials_path: Service Account JSON 경로
            cache_dir: 로컬 이미지 캐시 폴더
            settings_mgr: PublishSettingsManager 인스턴스 (인덱스 영속성용)
            group_name: 그룹명 (인덱스 저장용)
        """
        # Config 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Drive 이미지 루트 폴더 ID
        drive_config = self.config.get('google_drive', {})
        self.root_folder_id = drive_config.get('image_root_folder_id')

        # Drive API 연결
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly'
        ]

        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )

        self.service = build('drive', 'v3', credentials=creds)

        # 로컬 캐시 디렉토리
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # 스프레드시트 기반 인덱스 저장 (영속성)
        self.settings_mgr = settings_mgr
        self.group_name = group_name

        # 메모리 캐시 (폴백용, settings_mgr 없을 때만 사용)
        self._keyword_set_index: Dict[str, int] = {}

        self.log_callback: Optional[Callable[[str], None]] = None

    def set_group(self, group_name: str):
        """그룹명 설정 (런타임에 변경 가능)"""
        self.group_name = group_name

    def _get_index(self, keyword: str) -> int:
        """키워드 인덱스 가져오기 (스프레드시트 우선)"""
        if self.settings_mgr and self.group_name:
            return self.settings_mgr.get_image_index(self.group_name, keyword)
        return self._keyword_set_index.get(keyword, 0)

    def _set_index(self, keyword: str, index: int):
        """키워드 인덱스 저장 (스프레드시트 우선)"""
        if self.settings_mgr and self.group_name:
            self.settings_mgr.set_image_index(self.group_name, keyword, index)
        else:
            self._keyword_set_index[keyword] = index

    def set_log_callback(self, callback: Callable[[str], None]):
        """로그 콜백 설정"""
        self.log_callback = callback

    def log(self, message: str):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [ImageManager] {message}"
        print(log_msg)
        if self.log_callback:
            self.log_callback(message)

    def _find_folder_by_name(self, folder_name: str, parent_id: str = None) -> Optional[str]:
        """
        폴더 이름으로 폴더 ID 찾기

        Args:
            folder_name: 찾을 폴더 이름
            parent_id: 부모 폴더 ID (None이면 전체 검색)

        Returns:
            폴더 ID 또는 None
        """
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

        if parent_id:
            query += f" and '{parent_id}' in parents"

        try:
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

        except Exception as e:
            self.log(f"폴더 검색 오류: {e}")
            return None

    def _list_subfolders(self, folder_id: str) -> List[Dict]:
        """
        폴더 내 하위 폴더 목록 가져오기

        Args:
            folder_id: 부모 폴더 ID

        Returns:
            [{'id': str, 'name': str}, ...]
        """
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                orderBy='name',
                pageSize=100
            ).execute()

            return results.get('files', [])

        except Exception as e:
            self.log(f"하위 폴더 목록 오류: {e}")
            return []

    def _list_images_in_folder(self, folder_id: str) -> List[Dict]:
        """
        폴더 내 이미지 파일 목록 가져오기 (이름순 정렬)

        Args:
            folder_id: 폴더 ID

        Returns:
            [{'id': str, 'name': str, 'mimeType': str}, ...]
        """
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"

        try:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)',
                orderBy='name',
                pageSize=100
            ).execute()

            return results.get('files', [])

        except Exception as e:
            self.log(f"이미지 목록 오류: {e}")
            return []

    def _download_image(self, file_id: str, file_name: str, keyword: str) -> Optional[str]:
        """
        이미지 다운로드 (캐시 확인)

        Args:
            file_id: 파일 ID
            file_name: 파일 이름
            keyword: 키워드 (캐시 폴더 구분용)

        Returns:
            로컬 파일 경로 또는 None
        """
        # 캐시 경로
        keyword_cache_dir = os.path.join(self.cache_dir, self._safe_filename(keyword))
        os.makedirs(keyword_cache_dir, exist_ok=True)

        # 파일 ID를 해시하여 고유한 캐시 파일명 생성
        cache_filename = f"{file_id}_{file_name}"
        cache_path = os.path.join(keyword_cache_dir, cache_filename)

        # 이미 캐시에 있으면 바로 반환
        if os.path.exists(cache_path):
            return cache_path

        # 다운로드
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            # 파일 저장
            with open(cache_path, 'wb') as f:
                f.write(file_handle.getvalue())

            self.log(f"이미지 다운로드: {file_name}")
            return cache_path

        except Exception as e:
            self.log(f"이미지 다운로드 오류 ({file_name}): {e}")
            return None

    def _safe_filename(self, name: str) -> str:
        """파일명으로 사용 가능한 문자열로 변환"""
        # 특수문자 제거/치환
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name

    def get_keyword_folder_id(self, keyword: str) -> Optional[str]:
        """
        키워드 폴더 ID 가져오기

        Args:
            keyword: 키워드

        Returns:
            폴더 ID 또는 None
        """
        if not self.root_folder_id:
            self.log("Google Drive 루트 폴더 ID가 설정되지 않음")
            return None

        return self._find_folder_by_name(keyword, self.root_folder_id)

    def get_image_sets_for_keyword(self, keyword: str) -> List[Dict]:
        """
        키워드 폴더 내 이미지 세트(하위 폴더) 목록 가져오기

        Args:
            keyword: 키워드

        Returns:
            [{'id': str, 'name': str, 'image_count': int}, ...]
        """
        keyword_folder_id = self.get_keyword_folder_id(keyword)
        if not keyword_folder_id:
            self.log(f"키워드 폴더를 찾을 수 없음: {keyword}")
            return []

        subfolders = self._list_subfolders(keyword_folder_id)

        result = []
        for folder in subfolders:
            images = self._list_images_in_folder(folder['id'])
            result.append({
                'id': folder['id'],
                'name': folder['name'],
                'image_count': len(images)
            })

        self.log(f"키워드 '{keyword}' - {len(result)}개 이미지 세트 발견")
        return result

    def get_next_image_set(self, keyword: str) -> Optional[Dict]:
        """
        키워드에 대해 다음 이미지 세트 가져오기 (순환)

        Args:
            keyword: 키워드

        Returns:
            {'id': str, 'name': str, 'images': [local_path, ...]} 또는 None
        """
        image_sets = self.get_image_sets_for_keyword(keyword)

        if not image_sets:
            return None

        # 현재 인덱스 가져오기 (스프레드시트 우선, 없으면 0)
        current_index = self._get_index(keyword)

        # 순환
        if current_index >= len(image_sets):
            current_index = 0

        selected_set = image_sets[current_index]

        # 다음 인덱스 저장 (스프레드시트에 영속적으로 저장)
        self._set_index(keyword, current_index + 1)

        self.log(f"이미지 세트 선택: {selected_set['name']} ({current_index + 1}/{len(image_sets)})")

        # 이미지 다운로드
        images_info = self._list_images_in_folder(selected_set['id'])
        local_paths = []

        for img in images_info:
            local_path = self._download_image(img['id'], img['name'], keyword)
            if local_path:
                local_paths.append(local_path)

        return {
            'id': selected_set['id'],
            'name': selected_set['name'],
            'images': local_paths
        }

    def get_images_for_post(self, keyword: str, marker_count: int) -> List[str]:
        """
        한 포스트에 필요한 이미지 경로 목록 가져오기

        규칙:
        - 이미지 세트는 순환 (1 -> 2 -> 3 -> 1 ...)
        - marker_count > 이미지 수: 이미지 수만큼만 반환
        - marker_count < 이미지 수: 필요한 만큼만 반환

        Args:
            keyword: 키워드
            marker_count: 원고의 이미지 마커 개수

        Returns:
            로컬 이미지 파일 경로 리스트
        """
        if marker_count <= 0:
            return []

        image_set = self.get_next_image_set(keyword)

        if not image_set or not image_set['images']:
            self.log(f"키워드 '{keyword}'에 대한 이미지가 없음")
            return []

        images = image_set['images']

        # 마커 수와 이미지 수 중 작은 것 선택
        use_count = min(marker_count, len(images))

        self.log(f"이미지 {use_count}개 사용 (마커: {marker_count}, 세트 이미지: {len(images)})")

        return images[:use_count]

    def get_max_image_number_from_markers(self, content: str) -> int:
        """
        본문 내 이미지 마커에서 최대 이미지 번호 추출

        Args:
            content: 본문 내용 ({img:1}, {img:1-5} 형식 마커 포함)

        Returns:
            필요한 최대 이미지 번호 (마커가 없으면 0)
        """
        import re

        # {img:숫자} 또는 {img:숫자-숫자} 패턴
        marker_pattern = r'\{img:(\d+)(?:-(\d+))?\}'

        max_num = 0
        for match in re.finditer(marker_pattern, content):
            start_num = int(match.group(1))
            end_num = int(match.group(2)) if match.group(2) else start_num
            max_num = max(max_num, start_num, end_num)

        return max_num

    def get_images_for_content(self, keyword: str, content: str) -> List[str]:
        """
        본문 내 이미지 마커를 분석하여 필요한 이미지 가져오기

        {img:1-5} 형식: 1~5번 이미지 필요
        {img:3} 형식: 3번 이미지 필요

        Args:
            keyword: 키워드
            content: 본문 내용 (이미지 마커 포함)

        Returns:
            로컬 이미지 파일 경로 리스트 (인덱스 = 이미지번호 - 1)
        """
        max_image_num = self.get_max_image_number_from_markers(content)

        if max_image_num <= 0:
            self.log("이미지 마커 없음")
            return []

        return self.get_images_for_post(keyword, max_image_num)

    def reset_keyword_index(self, keyword: str = None):
        """
        키워드 이미지 세트 인덱스 초기화

        Args:
            keyword: 특정 키워드 (None이면 전체 초기화)
        """
        if self.settings_mgr and self.group_name:
            # 스프레드시트에서 초기화
            self.settings_mgr.reset_image_index(self.group_name, keyword)
            self.log(f"키워드 '{keyword or '전체'}' 인덱스 초기화 (스프레드시트)")
        else:
            # 메모리에서만 초기화
            if keyword:
                self._keyword_set_index.pop(keyword, None)
                self.log(f"키워드 '{keyword}' 인덱스 초기화")
            else:
                self._keyword_set_index.clear()
                self.log("전체 키워드 인덱스 초기화")

    def clear_cache(self, keyword: str = None):
        """
        이미지 캐시 삭제

        Args:
            keyword: 특정 키워드 (None이면 전체 삭제)
        """
        import shutil

        if keyword:
            keyword_cache_dir = os.path.join(self.cache_dir, self._safe_filename(keyword))
            if os.path.exists(keyword_cache_dir):
                shutil.rmtree(keyword_cache_dir)
                self.log(f"키워드 '{keyword}' 캐시 삭제")
        else:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
                self.log("전체 캐시 삭제")

    def test_connection(self) -> bool:
        """
        Google Drive 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            if not self.root_folder_id:
                self.log("루트 폴더 ID가 설정되지 않음")
                return False

            # 루트 폴더 접근 테스트
            folder = self.service.files().get(
                fileId=self.root_folder_id,
                fields='id, name'
            ).execute()

            self.log(f"Drive 연결 성공: {folder.get('name')}")
            return True

        except Exception as e:
            self.log(f"Drive 연결 실패: {e}")
            return False
