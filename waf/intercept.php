<?php
error_reporting(E_ALL);
define("WAF_DUMP_FILE", "/tmp/log-{time}.log");

class Intercept
{

    private $body = "";
    private $method = "UNKNOWN";
    private $protocol = "UNKNOWN";
    private $headers = array();
    private $data = array();

    function __construct()
    {
        $this->retrieve_headers();
        $this->data['time'] = $_SERVER['REQUEST_TIME'];
        $this->data['headers'] = $this->headers;
        $this->data['method'] = $this->method;
        $this->data['protocol'] = $this->protocol;
        $this->data['request'] = $this->body;
        $this->retrieveBody();
        $req = $this->requestContent();
        $ip = $_SERVER['REMOTE_ADDR'];
        $this->data['ip'] = $ip;
        $port = $_SERVER['REMOTE_PORT'];
        $this->data['port'] = $port;
        $this->writeLog("-----------------------\nFrom: $ip:$port;\n$req\n");
        ob_start();
    }

    function __destruct()
    {
        $this->responseCallback(ob_get_flush());
        $this->writeJsonLog();
    }

    /**
     * @param $content string
     * @return string
     */
    private function responseCallback($content)
    {
        $res = $this->responseContent($content);
        $this->writeLog("-----------------------\n$res\n");
        if(strpos($res, @file_get_contents("/flag"))!==false){
            $this->writeLog("^^^^^^^^^^^^^^^^^^^^^^^\nFLAG FOUND\n");
        }
    }

    private function retrieveBody()
    {
        $this->body = @file_get_contents('php://input');
        if (isset($this->body)) return;
        $this->body = @stream_get_contents(STDIN);
        if (isset($this->body)) return;
        $this->body = @http_get_request_body();
        if (isset($this->body)) return;
        $this->body = $GLOBALS["HTTP_RAW_POST_DATA"];
    }

    private function retrieve_headers()
    {
        $add_headers = array('CONTENT_TYPE', 'CONTENT_LENGTH');
        if (isset($_SERVER['HTTP_METHOD'])) {
            $this->method = $_SERVER['HTTP_METHOD'];
        } else if (isset($_SERVER['REQUEST_METHOD'])) {
            $this->method = $_SERVER['REQUEST_METHOD'];
        }
        if (isset($_SERVER['SERVER_PROTOCOL'])) {
            $this->protocol = $_SERVER['SERVER_PROTOCOL'];
        }
        foreach ($_SERVER as $i => $val) {
            if (strpos($i, 'HTTP_') === 0 || in_array($i, $add_headers)) {
                if (!$val)
                    continue;
                $name = @str_replace(array('HTTP_', '_'), array('', '-'), $i) ?: $i;
                $this->headers[$name] = $val;
            }
        }
    }

    public function requestContent()
    {
        $headers = $this->headers;
        $request = "$this->method {$_SERVER['REQUEST_URI']} $this->protocol\r\n";

        foreach ($headers as $i => $header) {
            $request .= "$i: $header\r\n";
        }
        $request .= "\r\n$this->body";
        return $request;
    }

    /**
     * @param $content string
     * @return string
     */
    public function responseContent($content)
    {
        $headers = @headers_list() ?: @apache_response_headers() ?: array();
        $status_code = @http_response_code() ?: "";
        $response = "$this->protocol $status_code\r\n";

        $this->data['status_code'] = $status_code;
        $this->data['response_headers'] = $headers;
        $this->data['response'] = $content;

        foreach ($headers as $i => $header) {
            $response .= "$header\r\n";
        }
        $response .= "\r\n$content";
        return $response;
    }

    private function getLogName()
    {
        $name = WAF_DUMP_FILE ?: "/tmp/dump.txt";
        return @str_replace("{time}", date("m-d-H-i"), $name) ?: $name;
    }

    public function writeLog($content)
    {
        @file_put_contents($this->getLogName(), $content, FILE_APPEND);
    }
    public function writeJsonLog()
    {
        @file_put_contents($this->getLogName().".json", json_encode($this->data)."\n", FILE_APPEND);
    }
}

if(!defined("INT")) {
    define("INT", 1);
    $_SERVER['__INTERCEPT'] = new Intercept();
}
