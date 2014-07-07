## dyf.fm

More pump, less dump!  Or, was it the other way around...?

### Requirements

- Python 2.7 
- PostgreSQL

### Installation

    $ git clone git@github.com:tensorjack/dyffm.git
    
    $ cd dyffm
    
    $ easy_install virtualenv
    
    $ virtualenv venv
    
    $ source venv/bin/activate
    
    $ apt-get install libxml2-dev libxslt1-dev
    
    $ pip install -r requirements.txt
    
    $ mv dyffm/config_local_sample.py dyffm/config_local.py (edit with real values) 
    
    $ ./manage.py clonedb
    
    $ ./manage.py runserver

### Unit tests

We love tests.  Our motto is, "Test the living shit out of everything!"

    $ nosetests
