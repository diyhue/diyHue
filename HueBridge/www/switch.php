<?php
if (!isset($_GET['mac'])) {
    exit();
}
require_once('bridge-config.php');
$con = mysqli_connect($dbip, $dbuser, $dbpass, $dbname);

function curl_request($address, $method, $body)
{
    $url = "http://127.0.0.1" . $address;

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Content-Type: application/json',
        'Content-Length: ' . strlen($body)
    ));
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);

}

$mac = $_GET['mac'];

$query_sensor = mysqli_query($con, "SELECT id, type FROM sensors WHERE uniqueid = '$mac' LIMIT 1;");
$row_cnt      = $query_sensor->num_rows;
if ($row_cnt == 0 && isset($_GET['devicetype'])) {
    echo "sensor must be registered \r\n";
    $device = $_GET['devicetype'];
    if ($device == 'ZLLSwitch') {
        $config    = '{"on":true,"battery":100,"reachable":true,"pending":[]}';
        $name      = 'Dimmer Switch';
        $modelid   = 'RWL021';
        $swversion = '5.45.1.17846';
    } else if ($device == 'ZGPSwitch') {
        $config    = '{"on":true}';
        $name      = 'Tap Switch';
        $modelid   = 'ZGPSWITCH';
        $swversion = '';
    }
    mysqli_query($con, "INSERT INTO `sensors` (`type`, `config`, `name`, `modelid`, `manufacturername`, `uniqueid`, `swversion`, `recycle`, `new`) VALUES ('$device', '$config', '$name', '$modelid', 'Philips', '$mac', '$swversion', 0, 1);");
} else {
    $row_sensor_id = mysqli_fetch_assoc($query_sensor);
    $sensor_id     = $row_sensor_id['id'];
    echo "sensor id: " . $sensor_id . " \r\n";
}
if (isset($_GET['button'])) {
    $button = $_GET['button'];
    echo "received button:" . $button . "\r\n";

    $query_rules = mysqli_query($con, "SELECT id, owner, actions, conditions FROM rules WHERE conditions LIKE '[{\"address\":\"/sensors/$sensor_id/state/buttonevent\",\"operator\":\"eq\",\"value\":\"$button\"}%';");
    $rules_cnt   = $query_rules->num_rows;
    if ($rules_cnt == 1) {
        echo "Found one rule \r\n";
        $row_rule      = mysqli_fetch_assoc($query_rules);
        $actions_array = json_decode($row_rule['actions'], true);
        foreach ($actions_array as $action) {
            curl_request('/api/' . $row_rule['owner'] . $action['address'], $action['method'], json_encode($action['body']));
        }
    } else if ($rules_cnt > 1) {
        echo "Found " . $rules_cnt . " rules \r\n";
        $i             = 0;
        $current_scene = 0;
        while ($row_rule = mysqli_fetch_assoc($query_rules)) {
            $conditions_array = json_decode($row_rule['conditions'], true);
            foreach ($conditions_array as $condition) {
                $address_pices = explode("/", $condition['address']);
                if (isset($address_pices[4]) && $address_pices[4] == "status") {
                    if ($i == 0) {
                        $query_sensor          = mysqli_query($con, "SELECT state FROM sensors WHERE id = $address_pices[2] LIMIT 1;");
                        $row_CLIPGenericStatus = mysqli_fetch_assoc($query_sensor);
                        if (empty($row_CLIPGenericStatus['state'])) {
                            $current_scene = 1;
                        } else {
                            $status        = json_decode($row_CLIPGenericStatus['state'], true);
                            $current_scene = $status['status'];
                        }
                        echo "current scene: $current_scene \r\n";
                    }
                    if (($condition['value'] == $current_scene && $condition['operator'] == 'eq') || ($condition['value'] < $current_scene && $condition['operator'] == 'gt') ||  ($condition['value'] > $current_scene && $condition['operator'] == 'lt')) {
                        $actions_array = json_decode($row_rule['actions'], true);

                        foreach ($actions_array as $action) {
                            curl_request('/api/' . $row_rule['owner'] . $action['address'], $action['method'], json_encode($action['body']));
                        }
                        mysqli_query($con, "UPDATE rules SET timestriggered = timestriggered + 1, lasttriggered = NOW() WHERE id = ".$row_rule['id'].";");
                    }
                }
            }
            $i++;
        }
    } else {
        echo "no rules where founded \r\n";
    }
    $sensor_state = array('buttonevent' => $button, 'lastupdated' => date("Y-m-d\TH:i:s"));
    mysqli_query($con, "UPDATE sensors SET state = '".json_encode($sensor_state)."' WHERE id = ". $sensor_id .";");

}
?>
