"""
UI 테마 상수

모든 GUI에서 공통으로 사용하는 색상, 폰트 등
"""


class Theme:
    """UI 테마 상수 클래스"""

    # 배경색
    BG_MAIN = '#f0f0f0'
    BG_MAIN_LIGHT = '#f5f5f5'  # 콘텐츠 생성기용
    BG_WHITE = 'white'
    BG_DARK = '#1a1a1a'
    BG_DARK_FOOTER = '#333'

    # 전경색 (텍스트)
    FG_TEXT = '#333'
    FG_TEXT_LIGHT = '#666'
    FG_TEXT_MUTED = '#999'
    FG_TEXT_MUTED_LIGHT = '#888'
    FG_TEXT_DARK = '#ccc'
    FG_TEXT_DARK_MUTED = '#aaa'

    # 상태 색상
    COLOR_SUCCESS = '#4CAF50'
    COLOR_ERROR = '#f44336'
    COLOR_WARNING = '#FF9800'
    COLOR_INFO = '#2196F3'
    COLOR_PURPLE = '#9C27B0'
    COLOR_PURPLE_DARK = '#673AB7'
    COLOR_GRAY = '#607D8B'

    # 상태 알림 배경색 (콘텐츠 생성기용)
    BG_STATUS_WARNING = '#FFF3CD'
    FG_STATUS_WARNING = '#856404'
    BG_STATUS_SUCCESS = '#D4EDDA'
    FG_STATUS_SUCCESS = '#155724'
    BG_STATUS_ERROR = '#F8D7DA'
    FG_STATUS_ERROR = '#721C24'
    BG_STATUS_INFO = '#D1ECF1'
    FG_STATUS_INFO = '#0C5460'
    BG_STATUS_HINT = '#E8F5E9'
    FG_STATUS_HINT = '#2E7D32'

    # 폰트
    FONT_FAMILY = '맑은 고딕'
    FONT_MONO = 'Consolas'

    FONT_NORMAL = (FONT_FAMILY, 9)
    FONT_NORMAL_BOLD = (FONT_FAMILY, 9, 'bold')
    FONT_MEDIUM = (FONT_FAMILY, 10)
    FONT_MEDIUM_BOLD = (FONT_FAMILY, 10, 'bold')
    FONT_SMALL = (FONT_FAMILY, 8)
    FONT_TINY = (FONT_FAMILY, 7)
    FONT_BOLD = (FONT_FAMILY, 9, 'bold')
    FONT_SMALL_BOLD = (FONT_FAMILY, 8, 'bold')
    FONT_TINY_BOLD = (FONT_FAMILY, 7, 'bold')

    FONT_LOG = (FONT_MONO, 8)

    # 트리뷰 행 색상
    TREE_ROW_AVAILABLE = '#e8f5e9'
    TREE_ROW_LOCKED = '#ffebee'

    # 구분선
    SEPARATOR_COLOR = '#ddd'

    @classmethod
    def get_log_colors(cls):
        """로그 레벨별 색상 반환"""
        return {
            'info': cls.FG_TEXT_DARK,
            'success': cls.COLOR_SUCCESS,
            'error': cls.COLOR_ERROR,
            'warning': cls.COLOR_WARNING
        }


# 편의를 위한 상수 별칭
COLORS = {
    'bg_main': Theme.BG_MAIN,
    'bg_white': Theme.BG_WHITE,
    'bg_dark': Theme.BG_DARK,
    'success': Theme.COLOR_SUCCESS,
    'error': Theme.COLOR_ERROR,
    'warning': Theme.COLOR_WARNING,
    'info': Theme.COLOR_INFO,
}

FONTS = {
    'normal': Theme.FONT_NORMAL,
    'small': Theme.FONT_SMALL,
    'tiny': Theme.FONT_TINY,
    'bold': Theme.FONT_BOLD,
    'log': Theme.FONT_LOG,
}
