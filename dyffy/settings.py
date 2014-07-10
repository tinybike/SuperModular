import os, sys, socket, re, logging

APP_NAME = 'dyffy'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = ['*']

DEPLOY_ENV = os.environ.get('DEPLOY_ENV', 'local')
DEBUG = True if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true' else False

# add libs to PYTHONPATH
sys.path.insert(0, os.path.join(PROJECT_ROOT, APP_NAME, "libs"))

SITE_ID = 1

TIME_ZONE = 'America/Vancouver'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = os.path.join(PROJECT_ROOT, APP_NAME, 'staticfiles')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, APP_NAME, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'e!2qskok^h9v_!klh-dq1@prhgfl2jwvp1=751x5xjquscq7phm'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
)

ROOT_URLCONF = '%s.urls' % APP_NAME

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = '%s.wsgi.application' % APP_NAME

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'south',
    'social_auth',
    'django_socketio',
    APP_NAME,
)

AUTHENTICATION_BACKENDS = (
    #    'social_auth.backends.twitter.TwitterBackend',
    'social_auth.backends.facebook.FacebookBackend',
    #    'social_auth.backends.google.GoogleOAuthBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    'social_auth.backends.google.GoogleBackend',
    'social_auth.backends.yahoo.YahooBackend',
    'social_auth.backends.contrib.linkedin.LinkedinBackend',
    #    'social_auth.backends.browserid.BrowserIDBackend',
    #    'social_auth.backends.contrib.livejournal.LiveJournalBackend',
    #    'social_auth.backends.contrib.orkut.OrkutBackend',
    #    'social_auth.backends.contrib.foursquare.FoursquareBackend',
    #    'social_auth.backends.contrib.github.GithubBackend',
    #    'social_auth.backends.contrib.vkontakte.VKontakteBackend',
    #    'social_auth.backends.contrib.live.LiveBackend',
    #    'social_auth.backends.contrib.skyrock.SkyrockBackend',
    'social_auth.backends.contrib.yahoo.YahooOAuthBackend',
    #    'social_auth.backends.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social_auth.backends.pipeline.social.social_auth_user',
    'social_auth.backends.pipeline.associate.associate_by_email',
    'social_auth.backends.pipeline.user.get_username',
    'social_auth.backends.pipeline.user.create_user',
    'social_auth.backends.pipeline.social.associate_user',
    'social_auth.backends.pipeline.user.update_user_details',
    'website.base.associate_new_user_profile',
)

AUTH_PROFILE_MODULE = '%s.Profile' % APP_NAME

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FACEBOOK_API_SECRET = os.environ.get('FACEBOOK_API_SECRET')

GOOGLE_OAUTH2_CLIENT_ID = os.environ.get('GOOGLE_OAUTH2_CLIENT_ID')
GOOGLE_OAUTH2_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH2_CLIENT_SECRET')
GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'access_type': 'offline'}
GOOGLE_EXTRA_DATA = [('oauth_token', 'oauth_token')]
GOOGLE_SREG_EXTRA_DATA = [('oauth_token', 'oauth_token')]
GOOGLE_AX_EXTRA_DATA = [('oauth_token', 'oauth_token')]

FACEBOOK_EXTENDED_PERMISSIONS = ['email', 'publish_stream']

LINKEDIN_CONSUMER_KEY = os.environ.get('LINKEDIN_CONSUMER_KEY')
LINKEDIN_CONSUMER_SECRET = os.environ.get('LINKEDIN_CONSUMER_SECRET')
# https://developer.linkedin.com/documents/profile-fields
LINKEDIN_SCOPE = ['r_basicprofile', 'r_emailaddress']
LINKEDIN_EXTRA_FIELD_SELECTORS = ['email-address', 'headline', 'industry', 'picture-url', 'first-name', 'last-name']
LINKEDIN_EXTRA_DATA = [
    ('id', 'id'),
    ('first-name', 'first_name'),
    ('last-name', 'last_name'),
    ('email-address', 'email_address'),
    ('headline', 'headline'),
    ('industry', 'industry'),
    ('picture-url', 'profile_picture')
]

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
POST_LOGIN_URL = '/'
#LOGIN_ERROR_URL = '/login-error/'
#LOGOUT_URL= '/logout/'

SOCIAL_AUTH_DEFAULT_USERNAME = 'new_social_auth_user'
SOCIAL_AUTH_UUID_LENGTH = 16

# honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

TEMPLATE_DEBUG = DEBUG
DEBUG_PROPAGATE_EXCEPTIONS = DEBUG

# settings_local.py overrides
if os.environ.get('DEPLOY_ENV') != 'prod':

    DEPLOY_ENV = 'local'
    DEBUG = True
    try:
        from settings_local import *
    except ImportError:
        print '\nYou must create a settings_local.py file.\n'
