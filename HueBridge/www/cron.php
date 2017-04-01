<?php

function curl_request($address, $method, $body){
$url = "http://127.0.0.1" . $address;

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json','Content-Length: ' . strlen($body)));
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
curl_setopt($ch, CURLOPT_POSTFIELDS,$body);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response  = curl_exec($ch);
curl_close($ch);

}

require_once('bridge-config.php');
$con = mysqli_connect($dbip, $dbuser, $dbpass, $dbname);
$query_schedules = mysqli_query($con, "SELECT * FROM schedules WHERE `status` = 'enabled';");
while ($row_schedules = mysqli_fetch_assoc($query_schedules)) {
   if ($row_schedules['local_time'][0] == "W") {
     $week_days = substr($row_schedules['local_time'], 1, strpos($row_schedules['local_time'], "/") -1 );
     $binary_week_days = decbin($week_days);
     $scheduler_time = substr($row_schedules['local_time'], strpos($row_schedules['local_time'], "T") + 1);
     if ($binary_week_days & (1 << 7 - date("N"))  && $scheduler_time == date('H:i:00')) {
       $data = json_decode($row_schedules['command'], true);
       curl_request($data['address'], $data['method'], json_encode($data['body']));
     }
   } else {
     if ($row_schedules['local_time'] == date("Y-m-d\TH:i:00")) {
       $data = json_decode($row_schedules['command'], true);
       curl_request($data['address'], $data['method'], json_encode($data['body']));
     }
   }
}
?>
