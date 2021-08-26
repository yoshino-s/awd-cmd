# awd.py
## 安装

Python3.9

```sh
pip install -r requirements.txt
```


```sh
./awd.py -i ip -p port -P password -u user
```

## 连接ssh

```sh
./awd.py -i ip -p port -P password -u user interactive
```

## 传文件

```sh
./awd.py -i ip -p port -P password -u user push local_file remote_file
./awd.py -i ip -p port -P password -u user push local_file remote_file
```

## 备份

```sh
./awd.py -i ip -p port -P password -u user backup html
./awd.py -i ip -p port -P password -u user backup db -u root -p root -d ctf
```

## 恢复

```sh
./awd.py -i ip -p port -P password -u user recovery html
./awd.py -i ip -p port -P password -u user recovery db -u root -p root -d ctf
```

## waf

### 上传

```sh
./awd.py -i ip -p port -P password -u user waf psuh
```

### watchbird

```sh
./awd.py -i ip -p port -P password -u user waf watchbird install -p birdwatch
./awd.py -i ip -p port -P password -u user waf watchbird uninstall
```

### intercept

```sh
./awd.py -i ip -p port -P password -u user waf intercept install
./awd.py -i ip -p port -P password -u user waf intercept uninstall
```

### 日志文件

```sh
./awd.py -i ip -p port -P password -u user waf log
```