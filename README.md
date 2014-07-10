## dyffy

### Requirements

- Python 2.7

### Installation

    $ git clone git@github.com:tensorjack/dyffm.git
    
    $ cd dyffm
    
    $ easy_install virtualenv
    
    $ virtualenv venv
    
    $ source venv/bin/activate
    
    $ pip install -r requirements.txt
    
    $ mv dyffm/config_local_sample.py dyffm/config_local.py (edit with real values) 
    
    $ ./manage.py initdb
    
    $ ./manage.py runserver
