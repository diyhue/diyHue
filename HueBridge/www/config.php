<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    $query_users = mysqli_query($con, 'SELECT * FROM users;');
    while ($row_users = mysqli_fetch_assoc($query_users)) {
        $array_whitelist[$row_users['username']] = array(
            'last use date' => $row_users['last_use_date'],
            'create_date' => $row_users['create_date'],
            'name' => $row_users['devicetype']
        );
    }
    $config_array = array(
        'portalservices' => false,
        'gateway' => $gateway,
        'mac' => $mac,
        'swversion' => '01036659',
        'apiversion' => '1.16.0',
        'linkbutton' => true,
        'ipaddress' => $ip_addres,
        'proxyport' => 0,
        'swupdate' => array(
            'updatestate' => 0,
            'checkforupdate' => false,
            'devicetypes' => new stdClass(),
            'text' => '',
            'notify' => false,
            'url' => ''
        ),
        'netmask' => '255.255.255.0',
        'name' => 'Philips hue',
        'dhcp' => true,
        'UTC' => gmdate("Y-m-d\TH:i:s"),
        'proxyaddress' => 'none',
        'localtime' => date("Y-m-d\TH:i:s"),
        'timezone' => 'Europe/Bucharest',
        'zigbeechannel' => '6',
        'modelid' => 'BSB001',
        'bridgeid' => '121FCFF69075',
        'factorynew' => false,
        'datastoreversion' => 59,
        'whitelist' => $array_whitelist
    );
    if ($print_entire_config) {
        $output_array['config'] = $config_array;
    } else {
        $output_array = $config_array;
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('CONFIG PUT: ' . json_encode($data));
    $output_array = array(
        'success' => array(
            '/' . $url['3'] . '/' . key($data) => $data[key($data)]
        )
    );
    error_log('config:' . json_encode($output_array, JSON_UNESCAPED_SLASHES));
}
