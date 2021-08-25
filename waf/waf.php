<?php
function install($dir, $file)
{
  $layer_list = scandir($dir);
  foreach ($layer_list as $i) {
    if ($i === '.' || $i === "..") {
      continue;
    }
    $next = $dir . $i;
    if (is_dir($next)) {
      if ($next[strlen($next) - 1] !== '/') {
        $next .= "/";
      }
      install($next, $file);
    } else {
      $ext = end(explode('.', $next));
      $php_ext = ["php", "php5", "phtml"];
      if (in_array($ext, $php_ext) && strlen($ext) !== strlen($next)) {
        $old_file_str = file_get_contents($next);
        if (strpos($old_file_str, "<?php") !== false && $next !== $file) {
          echo $next . "\n";
          $start_pos = strpos($old_file_str, "<?php");
          if ($start_pos === false) {
            return;
          }
          $first_code_pos1 = strpos($old_file_str, ";", $start_pos);
          $first_code_pos2 = strpos($old_file_str, "{", $start_pos);

          if ($first_code_pos1 === false) {
            $first_code_pos = $first_code_pos2;
          } else if ($first_code_pos2 === false) {
            $first_code_pos = $first_code_pos1;
          } else $first_code_pos = min($first_code_pos1, $first_code_pos2);
          if ($first_code_pos === false) {
            return;
          }
          while (strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "/*") !== false || strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "//") !== false || strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "#") !== false) {
            if (strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "/*") !== false) {
              $start_pos = strpos($old_file_str, "*/", strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "/*") + $start_pos);
              if ($start_pos === false) {
                return;
              }
              $first_code_pos1 = strpos($old_file_str, ";", $start_pos);
              $first_code_pos2 = strpos($old_file_str, "{", $start_pos);

              if ($first_code_pos1 === false) {
                $first_code_pos = $first_code_pos2;
              } else if ($first_code_pos2 === false) {
                $first_code_pos = $first_code_pos1;
              } else $first_code_pos = min($first_code_pos1, $first_code_pos2);
              if ($first_code_pos === false) {
                return;
              }
            }
            if (strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "//") !== false) {
              $start_pos = strpos($old_file_str, "\n", strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "//") + $start_pos);
              if ($start_pos === false) {
                return;
              }
              $first_code_pos1 = strpos($old_file_str, ";", $start_pos);
              $first_code_pos2 = strpos($old_file_str, "{", $start_pos);

              if ($first_code_pos1 === false) {
                $first_code_pos = $first_code_pos2;
              } else if ($first_code_pos2 === false) {
                $first_code_pos = $first_code_pos1;
              } else $first_code_pos = min($first_code_pos1, $first_code_pos2);
              if ($first_code_pos === false) {
                return;
              }
            }

            if (strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "#") !== false) {
              $start_pos = strpos($old_file_str, "\n", strrpos(substr($old_file_str, $start_pos, $first_code_pos - $start_pos), "#") + $start_pos);
              if ($start_pos === false) {
                return;
              }
              $first_code_pos1 = strpos($old_file_str, ";", $start_pos);
              $first_code_pos2 = strpos($old_file_str, "{", $start_pos);

              if ($first_code_pos1 === false) {
                $first_code_pos = $first_code_pos2;
              } else if ($first_code_pos2 === false) {
                $first_code_pos = $first_code_pos1;
              } else $first_code_pos = min($first_code_pos1, $first_code_pos2);
              if ($first_code_pos === false) {
                return;
              }
            }
          }
          if (preg_match("/namespace/i", substr($old_file_str, $start_pos, $first_code_pos - $start_pos)) === 1) {
            return;  // 一般来说, 只要加在入口文件即可
          } else if (preg_match("/declare {0,}\t{0,}\\(/i", substr($old_file_str, $start_pos, $first_code_pos - $start_pos)) === 1) {
            file_put_contents($next, substr($old_file_str, 0, $first_code_pos + 1) . "\ninclude_once '" . $file . "';\n" . substr($old_file_str, $first_code_pos + 1));
          } else {
            file_put_contents($next, "<?php include_once '" . $file . "'; ?>" . $old_file_str);
          }
        }
      }
    }
  }
}
function uninstall($dir, $file)
{
  $layer_list = scandir($dir);
  foreach ($layer_list as $i) {
    if ($i === '.' || $i == "..") {
      continue;
    }
    $next = $dir . $i;
    if (is_dir($next)) {
      if ($next[strlen($next) - 1] !== '/') {
        $next .= "/";
      }
      uninstall($next, $file);
    } else {
      $ext = end(explode('.', $next));
      $php_ext = ["php", "php5", "phtml"];
      if (in_array($ext, $php_ext) && strlen($ext) !== strlen($next)) {
        $old_file_str = file_get_contents($next);
        if (strpos(ltrim($old_file_str), "<?php include_once '" . $file . "'; ?>") === 0) {
          echo $next . "\n";
          file_put_contents($next, substr($old_file_str, strlen("<?php include_once '" . $file . "'; ?>")));
        } else {
          file_put_contents($next, str_replace("\ninclude_once '" . $file . "';\n", "", $old_file_str));
        }
      }
    }
  }
}



if (defined('STDIN')) {
  function usage()
  {
    $name = $argv[0];
    die("Usage: php $name install|uninstall [web dir] [waf path]");
  }
  if (sizeof($argv) != 4) {
    usage();
  }
  if (!in_array($argv[1], ["install", "uninstall"])) {
    usage();
  }
  $install_path = $argv[2];
  if ($install_path[strlen($install_path) - 1] !== '/') {
    $install_path .= "/";
  }
  $file = $argv[3];
  if ($argv[1] === "install") {
    install($install_path, $file);
  } elseif ($argv[1] === "uninstall") {
    uninstall($install_path, $file);
  } else {
    usage();
  }
}
