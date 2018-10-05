generate :
	command -v fades &>/dev/null || pip3 install --user fades && fades dockerfiles-generator.py

clean :
	rm -r output
