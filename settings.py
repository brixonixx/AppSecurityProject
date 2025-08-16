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

/* Remove underlines from navigation and dropdown links */
.navbar a, .dropdown-menu a, .nav-links a {{
    text-decoration: none !important;
}}

.dropdown-menu a:hover {{
    text-decoration: none !important;
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
        'login': 'Login',
        'home': 'Home',
        'dashboard': 'Dashboard',
        'events': 'Events',
        'profile_settings': 'Profile Settings',
        'security_settings': 'Security Settings',
        'signed_up_events': 'Signed-up Events',
        'admin_panel': 'Admin Panel',
        'admin_dashboard': 'Admin Dashboard',
        'user_management': 'User Management',
        'create_user': 'Create User',
        'volunteer_management': 'Volunteer Management',
        'audit_logs': 'Audit Logs',
        'export_users': 'Export Users',
        'account_information': 'Your Account Information',
        
        # Home page translations
        'welcome_back': 'Welcome back',
        'what_would_you_like_to_do': 'What would you like to do today?',
        'my_profile': 'My Profile',
        'view_update_personal_info': 'View and update your personal information',
        'view_account_statistics': 'View your account statistics and activity',
        'manage_security_preferences': 'Manage passwords, 2FA, and security preferences',
        'manage_users_system': 'Manage users and system settings',
        'account_at_glance': 'Your Account at a Glance',
        'account_status': 'Account Status',
        'active': 'Active',
        'member_since': 'Member Since',
        'last_login': 'Last Login',
        'first_login': 'This is your first login!',
        'account_type': 'Account Type',
        'administrator': 'Administrator',
        'standard_user': 'Standard User',
        'need_help': 'Need Help?',
        'contact_support_message': 'If you have any questions or need assistance, please don\'t hesitate to contact our support team.',
        'email_support': 'Email Support',
        'call_support': 'Call Support',
        'user_guide': 'User Guide',
        
        # Dashboard translations
        'profile_details': 'Profile Details',
        'name': 'Name',
        'email': 'Email',
        'age': 'Age',
        'contact': 'Contact',
        'not_set': 'Not set',
        'update_profile': 'Update Profile',
        'change_password': 'Change Password',
        
        # Volunteer translations
        'send_help_share_location': 'Send Help (Share Location)',
        'register_as_volunteer': 'Register as Volunteer',
        'click_button_to_share_location': 'Click the button above to share your location and request help.',
        'current_help_requests': 'Current Help Requests',
        'loading_map': 'Loading map...',
        
        # Events translations
        'exclusive_events': 'Exclusive Events',
        'sign_up_now': 'Sign Up Now!',
        'no_events_available': 'No events available at the moment.',
        'confirm_signup': 'Are you sure you want to sign up for'
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
        'login': '登录',
        'home': '主页',
        'dashboard': '仪表板',
        'events': '活动',
        'profile_settings': '个人设置',
        'security_settings': '安全设置',
        'signed_up_events': '已报名活动',
        'admin_panel': '管理面板',
        'admin_dashboard': '管理仪表板',
        'user_management': '用户管理',
        'create_user': '创建用户',
        'volunteer_management': '志愿者管理',
        'audit_logs': '审计日志',
        'export_users': '导出用户',
        'account_information': '您的账户信息',
        
        # Home page translations
        'welcome_back': '欢迎回来',
        'what_would_you_like_to_do': '您今天想做什么？',
        'my_profile': '我的个人资料',
        'view_update_personal_info': '查看和更新您的个人信息',
        'view_account_statistics': '查看您的账户统计和活动',
        'manage_security_preferences': '管理密码、双重验证和安全首选项',
        'manage_users_system': '管理用户和系统设置',
        'account_at_glance': '您的账户概览',
        'account_status': '账户状态',
        'active': '活跃',
        'member_since': '成员自',
        'last_login': '上次登录',
        'first_login': '这是您的首次登录！',
        'account_type': '账户类型',
        'administrator': '管理员',
        'standard_user': '标准用户',
        'need_help': '需要帮助？',
        'contact_support_message': '如果您有任何问题或需要帮助，请随时联系我们的支持团队。',
        'email_support': '邮件支持',
        'call_support': '电话支持',
        'user_guide': '用户指南',
        
        # Dashboard translations
        'profile_details': '个人详情',
        'name': '姓名',
        'email': '邮箱',
        'age': '年龄',
        'contact': '联系方式',
        'not_set': '未设置',
        'update_profile': '更新个人资料',
        'change_password': '更改密码',
        
        # Volunteer translations
        'send_help_share_location': '发送帮助（共享位置）',
        'register_as_volunteer': '注册为志愿者',
        'click_button_to_share_location': '点击上面的按钮来共享您的位置并请求帮助。',
        'current_help_requests': '当前帮助请求',
        'loading_map': '地图加载中...',
        
        # Events translations
        'exclusive_events': '专属活动',
        'sign_up_now': '立即报名！',
        'no_events_available': '目前没有可用的活动。',
        'confirm_signup': '您确定要报名参加'
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