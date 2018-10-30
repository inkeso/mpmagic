<?php include "../content/header.php"; ?>
<style>
/*body { background:#ddd; }*/
form { display:inline; }
/*input[type=submit] { border: none; background: #ddd; text-decoration:none; color: #a50; margin:0; padding:0; font:inherit;}
input[type=submit]:hover { color: #00f; background:#FACF8E; cursor:pointer;}
input[type=text] { border:1px dotted grey; padding:0; margin:0; background:#f4debc; }
input[type=text]:hover { border:1px solid grey; background: #facf8e; }*/
.magicbox { border:1px dashed #999; text-align:left; padding:.75em; display:inline-block; } /* background:#ddd} */
iframe { border:1px dashed #999; margin-top:5px; }
hr { border-top:1px dashed #999; margin:2px -5px; height:0; opacity: 0.2;}
ul { margin:2px; padding-left:1em;}
</style>
<?php
error_reporting(E_WARNING);
$classes = array("apl" => "AutoPlaylist", "jgl" => "Jingles", "mnt" => "Monitor");

function getit($cmd) {
    $buffer = "";
    if (strlen($cmd) > 0) {
        $socket = @fsockopen("127.0.0.1",55443);
        if (!$socket) die("<h1>MusicPlayerMagic not running</h1>");
        fwrite($socket, $cmd);
        while (!feof($socket)) { $buffer.= fgets($socket, 1024); }
        fclose($socket);
    }
    return $buffer;
}


if (isset($_POST['action'])) { // ACTIONS (COMMANDS) //
    $action = $_POST['action'];
    $class  = $_POST['class'];
    echo "<h2>".$classes[$class]." $action</h2><pre>";
    if ($action=='config') { // go through the POST and configure MPM
        $sww = false;
        foreach ($_POST as $key => $val) {
            if (get_magic_quotes_gpc())
                $val = stripslashes($val);
            if (preg_match("/^[sbn][FABDEIKMPS][a-z]+[DFLPMSU]?[a-z]+$/", $key)) {
                $resi = getit("$action $class $key $val");
                if ($resi != "True\n") $sww = true;
                echo "set $key to $val: <b style=\"color:".($resi=="True\n"?"green":"red").";\">$resi</b>";
            }
        }
        echo "</pre>";
        if ($sww === false)
             echo "<big style=\"color:green\"><b>All OK</b></big><script>window.setTimeout(\"parent.location.href='".$_SERVER['SCRIPT_NAME']."'\",1000);</script>";
    } else { // simple action
        echo getit("$action $class")."</pre>";
    }
    echo "</body></html>";

} else { // MAIN PAGE //
    // fetch and parse status
    $status = array();
    foreach (array_keys($classes) as $cls) {
        $vats = explode("\n", trim(getit("status $cls")));
        foreach ($vats as $row) {
            list($rn, $rv) = explode("\t", $row);
            $status[$cls][$rn] = $rv;
        }
    }

    // for my convinence
    function input($class, $name, $sd) {
        global $status;
        echo '<input type="text" name="'.$name.'" value=\''.$status[$class][$name].'\' size="'.$sd.'" />';
    }

    function formtag($class, $action) {
        echo '<form target="results" action="'.$_SERVER['SCRIPT_NAME'].'" method="POST">';
        echo '<input type="hidden" name="class" value="'.$class.'" />';
        echo '<input type="hidden" name="action" value="'.$action.'" />';
    }

    function submit($sd) {
            echo '<input type="submit" value="'.$sd.'" /></form>';
    }
    function toggleForm($wc) { // for Status-Toggle and heading
        global $status;
        global $classes;
        echo $classes[$wc];
        $sswitch = ($status[$wc]['service'] == "True" ? "OFF" : "ON");
        if ($status[$wc]['service'] == "True") {
            echo " (<b style='color:green'>active</b>)";
        } else {
            echo " (<b style='color:red'>inactive</b>)";
        }
        echo '<span style="float:right;">';
        formtag($wc, "config");
        echo '<input type="hidden" name="service" value="'.$sswitch.'" />';
        submit('Switch '.$sswitch);
        echo '</span>';
    }

    function actForm($wc, $ww, $desc) { // for Action
        formtag($wc, $ww);
        submit($desc);
    }
?>
<h1>Music Player Magic</h1>

<div class="magicbox">
    <b><?php toggleForm('apl'); ?></b>
    <hr/>
    <b><?php echo $status['apl']['blacklistlen'] + $status['apl']['played'] + $status['apl']['remain']; ?></b> Files in MPD-Database.<br/>
    <b><?php echo $status['apl']['blacklistlen']; ?></b> blacklisted, 
    <b><?php echo $status['apl']['played']; ?></b> <?php actForm('apl','history','already played'); ?>,
    <b><?php echo $status['apl']['remain']; ?></b> <?php actForm('apl','pool','remain in pool'); ?>
    &nbsp; :: &nbsp; <a href="/content/mpm_graph.php" target="results">Show statiscs</a>
    <hr>
    <?php formtag('apl','config'); ?>
    <ul>
      <li>Check playlist every <?php input('apl','interval',2); ?> seconds.</li>
      <li>Fill playlist with up to <?php input('apl','addfiles',2); ?> files and keep the last <?php input('apl','keepfiles',2); ?> in the list.</li>
      <li>Do not add files matching <?php input('apl','blacklist',30); ?></li>
    </ul>
    <hr>
    <span style="margin-left:15%;"><?php submit('Save changes'); ?></span>
    <span style="float:right;margin-right:15%;"><?php actForm('apl','refill','refill the pool" title="this will also empty the history'); ?></span>
</div>

<div class="magicbox">
    <b><?php toggleForm('jgl'); ?></b>
    <hr/>
    There are <?php actForm('jgl','pool',$status['jgl']['jingles']." Jingles"); ?> in the pool.<br/>
    Next one will be played in about <?php echo intval(($status['jgl']['nextjingle']-mktime())/60); ?> minutes (around <?php echo date("H:i",$status['jgl']['nextjingle'])?>)
    <hr/>
    <?php formtag('jgl','config'); ?>
    <ul>
      <li>In the directory <?php input('jgl', 'dir', '25'); ?></li>
      <li>Look for Jingles, matching the RegExp <?php input('jgl', 'ext', '15'); ?></li>
      <li>Play a random jingle every <?php input('jgl', 'minpause', '2'); ?> to <?php input('jgl', 'maxpause', '2'); ?>min.</li>
      <li>Wait for the last <?php input('jgl', 'secsleft', '1'); ?> seconds of the current song</li>
      <li>Reduce music-volume from <?php input('jgl', 'fadeup', '2'); ?>% to <?php input('jgl', 'fadedown', '2'); ?>% by <?php input('jgl', 'fadestep', '1'); ?>% every <?php input('jgl', 'fademsec', '2'); ?>ms</li>
      <li>Play the jingle with <?php input('jgl', 'player', '25'); ?></li>
    </ul>
    <hr>
    <span style="margin-left:15%;"><?php submit('Save changes'); ?></span>
    <span style="float:right;margin-right:15%;"><?php actForm('jgl','refill','refill the pool'); ?></span>
</div>


<div class="magicbox">
    <b><?php toggleForm('mnt'); ?></b>
    <hr/>
    <b>Logfile: </b><tt><?php echo $status['mnt']['logfile']; ?></tt>
</div>

<iframe src="about:blank" name="results" width="100%" height="600" frameborder="0"></iframe>

<?php
include "../content/footer.php";
}
?>
