import json
import os
import logging

logger = logging.getLogger(__name__)

# Default accessibility settings optimized for elderly users
DEFAULT_SETTINGS = {
    'font_size': 18,  # Larger default font for elderly
    'language': 'en',  # English or Chinese only
    'theme': 'light',  # light or dark only
}

def get_settings_dir():
    """Get or create settings directory"""
    settings_dir = os.path.join(os.getcwd(), 'user_settings')
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir, exist_ok=True)
    return settings_dir

def load_user_settings(user_id=None):
    """
    Load user settings from a file.
    Returns default settings if file doesn't exist.
    """
    try:
        settings_dir = get_settings_dir()
        
        if user_id:
            filename = os.path.join(settings_dir, f'user_{user_id}.json')
        else:
            filename = os.path.join(settings_dir, 'default_user.json')

        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_settings = DEFAULT_SETTINGS.copy()
                merged_settings.update(settings)
                logger.info(f"Loaded settings for user {user_id}: {merged_settings}")
                return merged_settings
        else:
            logger.info(f"No settings file found for user {user_id}, using defaults")
            return DEFAULT_SETTINGS.copy()
            
    except Exception as e:
        logger.error(f"Error loading settings for user {user_id}: {e}")
        return DEFAULT_SETTINGS.copy()


def save_user_settings(settings, user_id=None):
    """
    Save user settings to a file with validation.
    """
    try:
        settings_dir = get_settings_dir()
        
        if user_id:
            filename = os.path.join(settings_dir, f'user_{user_id}.json')
        else:
            filename = os.path.join(settings_dir, 'default_user.json')

        # Validate and clean settings
        cleaned_settings = {}

        # Font size validation (14-28px range)
        font_size = settings.get('font_size', 18)
        try:
            font_size = int(font_size)
            if 14 <= font_size <= 28:
                cleaned_settings['font_size'] = font_size
            else:
                cleaned_settings['font_size'] = 18
        except (ValueError, TypeError):
            cleaned_settings['font_size'] = 18

        # Language validation (only English and Chinese)
        language = settings.get('language', 'en')
        if language in ['en', 'zh']:
            cleaned_settings['language'] = language
        else:
            cleaned_settings['language'] = 'en'

        # Theme validation (only light and dark)
        theme = settings.get('theme', 'light')
        if theme in ['light', 'dark']:
            cleaned_settings['theme'] = theme
        else:
            cleaned_settings['theme'] = 'light'

        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cleaned_settings, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Settings saved for user {user_id}: {cleaned_settings}")
        return True

    except Exception as e:
        logger.error(f"Error saving settings for user {user_id}: {e}")
        return False


def get_accessibility_css(settings):
    """
    Generate CSS based on accessibility settings optimized for elderly users.
    """
    font_size = settings.get('font_size', 18)
    theme = settings.get('theme', 'light')

    css = f"""<style>
:root {{
    --base-font-size: {font_size}px;
    --border-radius: 8px;
    --focus-outline: 3px solid #007bff;
}}

/* Base typography for elderly users */
body {{
    font-family: 'Arial', 'Helvetica', sans-serif !important;
    font-size: var(--base-font-size) !important;
    line-height: 1.6 !important;
    letter-spacing: 0.5px !important;
}}

/* Headings with proper size scaling */
h1 {{ font-size: calc(var(--base-font-size) * 2.2) !important; font-weight: bold !important; }}
h2 {{ font-size: calc(var(--base-font-size) * 1.8) !important; font-weight: bold !important; }}
h3 {{ font-size: calc(var(--base-font-size) * 1.5) !important; font-weight: bold !important; }}
h4 {{ font-size: calc(var(--base-font-size) * 1.3) !important; font-weight: bold !important; }}
h5 {{ font-size: calc(var(--base-font-size) * 1.2) !important; font-weight: bold !important; }}
h6 {{ font-size: calc(var(--base-font-size) * 1.1) !important; font-weight: bold !important; }}

/* Content areas */
.forum-content, .post-content, .comment-content, 
p, .card-text, .form-control, .form-select, .btn {{
    font-size: var(--base-font-size) !important;
    line-height: 1.6 !important;
}}

/* Enhanced buttons for elderly users */
.btn {{
    padding: 15px 25px !important;
    font-size: calc(var(--base-font-size) + 2px) !important;
    font-weight: bold !important;
    border-radius: var(--border-radius) !important;
    border-width: 2px !important;
    min-height: 48px !important;
    cursor: pointer !important;
}}

/* Enhanced form controls */
.form-control, .form-select {{
    padding: 12px 16px !important;
    font-size: var(--base-font-size) !important;
    border-width: 2px !important;
    border-radius: var(--border-radius) !important;
    min-height: 48px !important;
}}

/* Navigation improvements */
.navbar-nav .nav-link {{
    font-size: calc(var(--base-font-size) + 2px) !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
}}

/* Enhanced focus indicators for accessibility */
*:focus {{
    outline: var(--focus-outline) !important;
    outline-offset: 2px !important;
}}

/* Link improvements */
a {{
    text-decoration: underline !important;
    font-weight: 500 !important;
}}

/* Card and content spacing */
.card {{
    padding: 20px !important;
    margin-bottom: 20px !important;
}}

.card-body {{
    padding: 25px !important;
}}
"""

    # Theme-specific styles
    if theme == 'dark':
        css += """
/* Dark theme for reduced eye strain */
body {
    background-color: #121212 !important;
    color: #ffffff !important;
}

.card, .form-control, .form-select, .modal-content {
    background-color: #1e1e1e !important;
    border-color: #444 !important;
    color: #ffffff !important;
}

.btn-primary {
    background-color: #4dabf7 !important;
    border-color: #4dabf7 !important;
    color: #000 !important;
}

.btn-secondary, .btn-outline-secondary {
    background-color: #6c757d !important;
    border-color: #6c757d !important;
    color: #fff !important;
}

.alert {
    background-color: #2d2d2d !important;
    border-color: #444 !important;
    color: #ffffff !important;
}

.table {
    background-color: #1e1e1e !important;
    color: #ffffff !important;
}

.table th, .table td {
    border-color: #444 !important;
}

/* Fix white sections in dark mode */
.setting-section, .preview-text {
    background-color: #1e1e1e !important;
    color: #ffffff !important;
    border-color: #444 !important;
}

.theme-card {
    background-color: #2d2d2d !important;
    color: #ffffff !important;
    border-color: #555 !important;
}

.language-btn {
    background-color: #2d2d2d !important;
    color: #ffffff !important;
    border-color: #4dabf7 !important;
}

.language-btn.active {
    background-color: #4dabf7 !important;
    color: #000000 !important;
}

/* Fix dropdown and select elements */
select, option {
    background-color: #1e1e1e !important;
    color: #ffffff !important;
}

/* Fix input elements */
input[type="range"] {
    background-color: #1e1e1e !important;
}
"""
    else:  # Light theme (default)
        css += """
/* Light theme with enhanced readability */
body {
    background-color: #ffffff !important;
    color: #333333 !important;
}

.card {
    background-color: #ffffff !important;
    border: 2px solid #dee2e6 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

.form-control, .form-select {
    background-color: #ffffff !important;
    border: 2px solid #ced4da !important;
    color: #333333 !important;
}

.form-control:focus, .form-select:focus {
    border-color: #007bff !important;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25) !important;
}

.btn-primary {
    background-color: #007bff !important;
    border-color: #007bff !important;
    color: #ffffff !important;
}

.btn-primary:hover {
    background-color: #0056b3 !important;
    border-color: #0056b3 !important;
}

.alert-success {
    background-color: #d4edda !important;
    border-color: #c3e6cb !important;
    color: #155724 !important;
}

.alert-danger {
    background-color: #f8d7da !important;
    border-color: #f5c6cb !important;
    color: #721c24 !important;
}
"""

    # Additional elderly-friendly improvements
    css += """

/* Improved spacing and readability */
.container, .container-fluid {
    padding: 20px !important;
}

/* Enhanced table readability */
.table {
    font-size: var(--base-font-size) !important;
}

.table th, .table td {
    padding: 15px !important;
    vertical-align: middle !important;
}

/* Improved form spacing */
.form-group, .mb-3 {
    margin-bottom: 25px !important;
}

.form-label {
    font-weight: bold !important;
    margin-bottom: 8px !important;
    font-size: calc(var(--base-font-size) + 1px) !important;
}

/* Mobile responsiveness for elderly users */
@media (max-width: 768px) {
    body {
        font-size: calc(var(--base-font-size) + 2px) !important;
    }

    .btn {
        padding: 18px 30px !important;
        font-size: calc(var(--base-font-size) + 2px) !important;
        min-height: 54px !important;
    }

    .form-control, .form-select {
        padding: 16px 20px !important;
        font-size: calc(var(--base-font-size) + 2px) !important;
        min-height: 54px !important;
    }

    .navbar-nav .nav-link {
        padding: 15px 20px !important;
        font-size: calc(var(--base-font-size) + 3px) !important;
    }
}
</style>"""

    return css


# Language text dictionary for the interface - COMPLETE VERSION
INTERFACE_TEXTS = {
    'en': {
        'settings_title': 'Settings',
        'text_size': 'Text Size',
        'language': 'Language',
        'display_mode': 'Display Mode',
        'save_settings': 'Save My Settings',
        'settings_saved': 'Settings saved successfully!',
        'bright_background': 'Bright Background',
        'dark_background': 'Dark Background',
        'make_text_bigger': 'Make text bigger or smaller:',
        'choose_language': 'Choose your preferred language:',
        'choose_display': 'Choose how the screen looks:',
        'preview_text': 'This is how your text will look. You can make it bigger or smaller using the slider above.',
        'easy_bright_rooms': 'Easy to read in bright rooms',
        'easier_night': 'Easier on the eyes at night',

        # Navigation and common elements
        'community_forum': 'Community Forum',
        'calendar': 'Calendar',
        'forum': 'Forum',
        'volunteers': 'Volunteers',
        'chatbot': 'AI Assistant',
        'faq': 'FAQ',
        'help': 'Help',
        'settings': 'Settings',
        'community_footer': 'Community Forum - Stay Connected',

        # Forum-specific texts
        'new_post': 'New Post',
        'view_posts': 'View Posts',
        'view_post': 'View Post',
        'post_title': 'Post Title',
        'post_content': 'Post Content',
        'comments': 'comments',
        'add_comment': 'Add Comment',
        'edit_post': 'Edit Post',
        'delete_post': 'Delete',
        'submit': 'Submit',
        'cancel': 'Cancel',
        'by': 'Posted by',
        'on': 'On',
        'no_posts_yet': 'No posts yet. Be the first to post!',
        'confirm_delete': 'Are you sure you want to delete this post?',

        # Volunteer-specific texts
        'volunteer_requests': 'Volunteer Requests',
        'new_request': 'New Request',
        'request_help': 'Request Help',
        'offer_help': 'Offer Help',
        'claim_request': 'Claim Request',
        'requested_by': 'Requested by',
        'claimed_by': 'Claimed by',

        # General UI texts
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'warning': 'Warning',
        'info': 'Information',
        'close': 'Close',
        'back': 'Back',
        'next': 'Next',
        'previous': 'Previous',
        'search': 'Search',
        'filter': 'Filter',
        'sort': 'Sort',
        'date': 'Date',
        'time': 'Time',
        'author': 'Author',
        'title': 'Title',
        'description': 'Description',
        'welcome': 'Welcome',
        'logout': 'Logout',
        'login': 'Login'
    },
    'zh': {
        'settings_title': '设置',
        'text_size': '文字大小',
        'language': '语言',
        'display_mode': '显示模式',
        'save_settings': '保存设置',
        'settings_saved': '设置保存成功！',
        'bright_background': '明亮背景',
        'dark_background': '深色背景',
        'make_text_bigger': '调整文字大小：',
        'choose_language': '选择您的首选语言：',
        'choose_display': '选择屏幕显示方式：',
        'preview_text': '这是您的文字显示效果。您可以使用上面的滑块来调整文字大小。',
        'easy_bright_rooms': '适合明亮环境阅读',
        'easier_night': '夜间阅读更舒适',

        # Navigation and common elements
        'community_forum': '社区论坛',
        'calendar': '日历',
        'forum': '论坛',
        'volunteers': '志愿者',
        'chatbot': 'AI助手',
        'faq': '常见问题',
        'help': '帮助',
        'settings': '设置',
        'community_footer': '社区论坛 - 保持联系',

        # Forum-specific texts
        'new_post': '新帖子',
        'view_posts': '查看帖子',
        'view_post': '查看帖子',
        'post_title': '帖子标题',
        'post_content': '帖子内容',
        'comments': '评论',
        'add_comment': '添加评论',
        'edit_post': '编辑帖子',
        'delete_post': '删除',
        'submit': '提交',
        'cancel': '取消',
        'by': '发布者',
        'on': '于',
        'no_posts_yet': '暂无帖子。成为第一个发帖的人！',
        'confirm_delete': '您确定要删除这个帖子吗？',

        # Volunteer-specific texts
        'volunteer_requests': '志愿者请求',
        'new_request': '新请求',
        'request_help': '请求帮助',
        'offer_help': '提供帮助',
        'claim_request': '认领请求',
        'requested_by': '请求者',
        'claimed_by': '认领者',

        # General UI texts
        'loading': '加载中...',
        'error': '错误',
        'success': '成功',
        'warning': '警告',
        'info': '信息',
        'close': '关闭',
        'back': '返回',
        'next': '下一页',
        'previous': '上一页',
        'search': '搜索',
        'filter': '筛选',
        'sort': '排序',
        'date': '日期',
        'time': '时间',
        'author': '作者',
        'title': '标题',
        'description': '描述',
        'welcome': '欢迎',
        'logout': '注销',
        'login': '登录'
    }
}


def get_language_text(settings, key, texts=None):
    """
    Get text in the user's preferred language.
    """
    if texts is None:
        texts = INTERFACE_TEXTS

    language = settings.get('language', 'en')
    return texts.get(language, texts.get('en', {})).get(key, key)


def validate_elderly_settings(settings):
    """
    Additional validation specifically for elderly users.
    Ensures settings are safe and appropriate.
    """
    # Ensure font size is not too small for elderly users
    if settings.get('font_size', 18) < 16:
        settings['font_size'] = 16

    return settings