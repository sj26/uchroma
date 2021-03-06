DESTDIR?=/
PYTHONDIR?=$(shell python3 -c 'import sys; print(sys.path[-1])')

purge_pycache:
	@find -name '__pycache__' | xargs rm -rf

clean: purge_pycache
	@rm -rf build dist uchroma.egg-info
	make -C doc clean

install_library: purge_pycache
	python3 setup.py install --root=$(DESTDIR)

cython_inplace:
	python3 setup.py build_ext --inplace

install_udev: cython_inplace
	install -m 644 -v -D install/70-uchroma.rules $(DESTDIR)/etc/udev/rules.d/70-uchroma.rules
	$(eval HWDB := $(shell mktemp))
	python3 setup.py -q hwdb > $(HWDB)
	install -m 644 -v -D $(HWDB) $(DESTDIR)/etc/udev/hwdb.d/70-uchroma.hwdb
	@rm -v -f $(HWDB)

install_service:
	install -m 644 -v -D install/org.chemlab.UChroma.service $(DESTDIR)/usr/share/dbus-1/services/org.chemlab.UChroma.service
	install -m 644 -v -D install/uchromad.service $(DESTDIR)/usr/lib/systemd/user/uchromad.service

uninstall_library:
	$(eval UCPATH := $(wildcard $(DESTDIR)/usr/local/lib/python3*/*/uchroma))
	$(if $(UCPATH), $(eval EGGPATH := $(shell readlink -f $(UCPATH)-*.egg-info/)))
	@rm -v -rf $(UCPATH)
	@rm -v -rf $(EGGPATH)
	@rm -v -f $(DESTDIR)/usr/local/bin/uchroma
	@rm -v -f $(DESTDIR)/usr/local/bin/uchromad

uninstall_udev:
	@rm -v -f $(DESTDIR)/etc/udev/rules.d/70-uchroma.rules
	@rm -v -f $(DESTDIR)/etc/udev/hwdb.d/70-uchroma.hwdb

uninstall_service:
	@rm -v -f $(DESTDIR)/usr/share/dbus-1/services/org.chemlab.UChroma.service
	@rm -v -f $(DESTDIR)/usr/lib/systemd/user/uchromad.service

sphinx_clean:
	@rm -f doc/uchroma.*

sphinx: sphinx_clean cython_inplace
	sphinx-apidoc -o doc -M -f -e .

docs: sphinx
	make -C doc html

install: install_library install_udev install_service

uninstall: uninstall_library uninstall_udev uninstall_service

dist:
	python3 setup.py sdist --dist-dir=../ --formats=xztar

dist_orig: dist
	rename -f 's/uchroma-(.*)\.tar\.xz/uchroma_$$1\.orig\.tar\.xz/' ../*

debs: dist_orig
	debuild -i -us -uc -b

deb-src: dist_orig
	rename -f 's/uchroma-(.*)\.tar\.xz/uchroma_$$1\.orig\.tar\.xz/' ../*
	debuild -S -i -I

test:
	pytest

all: install docs

up:
	python3 setup.py install --user
