"""
Django settings for dailyfresh project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 为什么不加在0号位？因为0号位是当前目录''
sys.path.insert(1, os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9nkw@i8f4b!+)r$gd=xbs02!%zcic2$5442%%uyxsg5ano=7db'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    # django默认开启用户认证模块
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'haystack',
    'tinymce',
    'users',
    'goods',
    'orders',
    'cart',
)

# AUTH_USER_MODEL = '应用.用户模型类'   固定格式，所以要配合把apps设为可导入的路径
# django 认证系统使用的user模型类
AUTH_USER_MODEL = 'users.User'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # django默认开启用户认证中间块
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'dailyfresh.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],

        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dailyfresh.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'dailyfresh',
        'HOST': 'localhost',  # mysql主服务器，在本地
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': 'mima',
    },
    # 'slave': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'NAME': 'dailyfresh',
    #     'HOST': '192.168.47.69',   # mysql从服务器，在windows中
    #     'PORT': '3306',
    #     'USER': 'root',
    #     'PASSWORD': 'mima',
    # },
}

# 配置读写分离
# DATABASE_ROUTERS = ['utils.db_router.MasterSlaveDBRouter']

# session保存在redis中
# SESSION_ENGINE = 'redis_sessions.session'
# SESSION_REDIS_HOST = 'localhost'
# SESSION_REDIS_PORT = 6379
# SESSION_REDIS_DB = 2
# SESSION_REDIS_PASSWORD = ''
# SESSION_REDIS_PREFIX = 'session'

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'  # 此处的static是url路径

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')  # 此处的static是文件路径
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'static/media')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # 导入邮件模块
EMAIL_HOST = 'smtp.163.com'  # 发邮件主机
EMAIL_PORT = 25  # 发邮件端口
EMAIL_HOST_USER = 'luckey_one@163.com'  # 授权的邮箱
EMAIL_HOST_PASSWORD = 'q1w2e3r4'  # 邮箱授权时获得的密码，非注册登录密码
EMAIL_FROM = '国务院<luckey_one@163.com>'  # 发件人抬头

# 缓存
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/5",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    },
}

# Session
# http://django-redis-chs.readthedocs.io/zh_CN/latest/#session-backend

# 指定session存在redis里
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# 已登录状态认证失败后跳转的路径
LOGIN_URL = '/users/login/'

# 配置Django自定义的文件存储系统
DEFAULT_FILE_STORAGE = 'utils.fastdfs.storage.FastDFSStorage'

# ret = {
# 	'Group name':'group1',
# 	'Status':'Upload successed.',
# 	'Remote file_id':'group1/M00/00/00/wKjzh0_xaR63RExnAAAaDqbNk5E1398.py',
# 	'Uploaded size':'6.0KB',
# 	'Local file name':'test',
# 	 'Storage IP':'192.168.243.133'
# }

# FastFDS使用的配置信息
CLIENT_CONF = os.path.join(BASE_DIR, 'utils/fastdfs/client.conf')
SERVER_IP = 'http://192.168.141.130:8888/'

# 富文本编辑config配置
TINYMCE_DEFAULT_CONFIG = {
  'theme': 'advanced', # 丰富样式
  'width': 600,
  'height': 400,
}

# 配置搜索引擎后端
HAYSTACK_CONNECTIONS = {
  'default': {
      # 使用whoosh引擎：提示，如果不需要使用jieba框架实现分词，就使用whoosh_backend
      'ENGINE': 'haystack.backends.whoosh_cn_backend.WhooshEngine',
      # 索引文件路径
      'PATH': os.path.join(BASE_DIR, 'whoosh_index'),
  }
}

# 当添加、修改、删除数据时，自动生成索引
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
# 搜索结果每页显示数量
HAYSTACK_SEARCH_RESULTS_PER_PAGE = 2