all : silva-restserver.tmp rest-server.tmp silva-restserver-test.tmp
	@echo Complete

silva-restserver.tmp: silva-restserver
	@sudo cp silva-restserver /etc/init.d
	@sudo update-rc.d silva-restserver defaults
	@touch silva-restserver.tmp

rest-server.tmp: rest-server.py required.txt
	# Settings.py are are only copied if they don't exists as the user
	# has most likley changed them.
	@sudo pip3 install -r required.txt
	@[ -d /usr/share/silva-restserver ] || sudo mkdir /usr/share/silva-restserver
	@[ -f /usr/share/silva-restserver/settings.py ] || sudo cp settings.py /usr/share/silva-restserver/settings.py
	@sudo cp rest-server.py /usr/share/silva-restserver/rest-server
	@sudo chmod a+x /usr/share/silva-restserver/rest-server
	@touch rest-server.tmp

silva-restserver-test.tmp: silva-restserver-test
	@sudo cp silva-restserver-test /etc/init.d
	@sudo update-rc.d silva-restserver-test defaults
	@touch silva-restserver-test.tmp

clean:
	@rm -f *tmp
	@echo "Cleaned up"

remove:
	@sudo update-rc.d -f silva-restserver remove
	@sudo update-rc.d -f silva-restserver-test remove
	@echo "Removed"
