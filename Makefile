all: attachments packages zincsearch

attachments:
	mkdir -p attachments
	wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.1/pspy64 -O attachments/pspy64
	chmod +x attachments/pspy64
	wget https://dl.shellpub.com/hm/latest/hm-linux-amd64.tgz?version=1.8.3 -O attachments/hm-linux-amd64.tgz
	mkdir -p attachments/hema
	tar -xvf attachments/hm-linux-amd64.tgz -C attachments/hema
	rm attachments/hm-linux-amd64.tgz

packages:
	tar -czvf attachments.tgz attachments
	tar -czvf waf.tgz waf

zincsearch:
  mkdir -p zincsearch
	chmod 777 zincsearch
