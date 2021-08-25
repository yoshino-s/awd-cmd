<?php
error_reporting(E_ALL);
define("WAF_DUMP_FILE", "/tmp/log-{time}.log");

class Intercept
{

    private $body = "";
    private $method = "UNKNOWN";
    private $protocol = "UNKNOWN";
    private $headers = array();
    /**
     * @var string
     */
    private $uuid;

    function __construct()
    {
        $this->retrieve_headers();
        $this->retrieveBody();
        $req = $this->requestContent();
        $this->uuid = uniqid();
        $ip = $_SERVER['REMOTE_ADDR'];
        $port = $_SERVER['REMOTE_PORT'];
        $this->writeLog("-----------------------\nFrom: $ip:$port;\n$this->uuid\n$req\n");
        ob_start(function ($i) {
            return $this->responseCallback($i);
        });
    }

    /**
     * @param $content string
     * @return string
     */
    private function responseCallback($content)
    {
        $res = $this->responseContent($content);
        $this->writeLog("-----------------------\n$this->uuid\n$res\n");
        return $content;
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
        if (isset($this->request)) {
            return $this->request;
        }
        $headers = $this->headers;
        $this->request = "$this->method {$_SERVER['REQUEST_URI']} $this->protocol\r\n";

        foreach ($headers as $i => $header) {
            $this->request .= "$i: $header\r\n";
        }
        $this->request .= "\r\n$this->body";
        return $this->request;
    }

    /**
     * @param $content string
     * @return string
     */
    public function responseContent($content)
    {
        if (isset($this->response)) {
            return $this->response;
        }
        $headers = @headers_list() ?: @apache_response_headers() ?: array();
        $status_code = @http_response_code() ?: "";
        $this->response = "$this->protocol $status_code\r\n";

        foreach ($headers as $i => $header) {
            $this->response .= "$header\r\n";
        }
        $this->response .= "\r\n$content";
        return $this->response;
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
}

if(!defined("INT")) {
    define("INT", 1);
    new Intercept();
}
