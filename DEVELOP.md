# Using the development buildout


## plonecli

The convenient way, use plonecli build ;)

```shell
plonecli build
 ```

or with --clear if you want to clean your existing venv

```shell
plonecli build --clear
```

Start your instance

```shell
plonecli serve
```


## Without plonecli

Create a virtualenv in the package
```shell
python3 -m venv venv
```

or with --clear if you want to clean your existing venv
```shell
python3 -m venv venv --clear
```

Install requirements with pip
```shell
`./venv/bin/pip install -r requirements.txt
```

bootstrap your buildout
```shell
./bin/buildout bootstrap
```

Run buildout
```shell
./bin/buildout
```

Start Plone in foreground
```shell
./bin/instance fg
```


## Running tests

```shell
tox
```

list all tox environments::

```shell
tox -l
```

run a specific tox env::

```shell
tox -e py312-Plone60
```
