# install python3 environment

```
sudo apt-get update

sudo apt-get install -y python-pip python-dev mysql-server libmysqlclient-dev virtualenv make

sudo apt-get install build-essential python-dev python3-dev
sudo apt-get install python3.6-dev

```
# configure project

```
virtualenv venv -p python3

source venv/bin/activate

git clone -b eluminate_web_dev https://gitlab.com/eluminate-group/eluminate_web.git

cd eluminate_web

make install

make localrun

```

# http://127.0.0.1:8080


