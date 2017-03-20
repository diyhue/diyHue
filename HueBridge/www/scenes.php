<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_scenes = mysqli_query($con, "SELECT *, DATE_FORMAT(lastupdated, '%Y-%m-%dT%T') AS lastupdated_converted FROM scenes;");
        while ($row_scenes = mysqli_fetch_assoc($query_scenes)) {
            $query_lightstates = mysqli_query($con, 'SELECT * FROM lightstates WHERE scene_id = '.$row_scenes['id'].';');
            while ($row_lightstates = mysqli_fetch_assoc($query_lightstates)) {
                $lightstates_array[$row_lightstates['light_id']] = array(
                        'on' => (bool) $row_lightstates['state'],
                        'bri' => intval($row_lightstates['bri']),
                        (($row_lightstates['xy'] != '') ? 'xy' : 'ct') => (($row_lightstates['xy'] != '') ? json_decode($row_lightstates['xy'], true) : intval($row_lightstates['ct'])),
                    );
                if ($row_lightstates['transitiontime'] != '0') {
                    $lightstates_array[$row_lightstates['light_id']]['transitiontime'] = (int) $row_lightstates['transitiontime'];
                }
            }
            $scene_array[$row_scenes['id']] = array(
                    'name' => $row_scenes['name'],
                    'lights' => json_decode($row_scenes['lights'], true),
                    'owner' => $row_scenes['owner'],
                    'recycle' => (bool) $row_scenes['recycle'],
                    'locked' => (bool) $row_scenes['locked'],
                    'appdata' => json_decode($row_scenes['appdata'], true),
                    'picture' => $row_scenes['picture'],
                    'lastupdated' => $row_scenes['lastupdated_converted'],
                    'version' => 2,
                    'lightstates' => $lightstates_array,
                );
        }
        if (isset($scene_array)) {
            if ($print_entire_config) {
                $output_array['scenes'] = $scene_array;
            } else {
                $output_array = $scene_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['scenes'] = new stdClass();
            } else {
                $output_array = new stdClass();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_scene = mysqli_query($con, "SELECT *, DATE_FORMAT(lastupdated, '%Y-%m-%dT%T') AS lastupdated_converted FROM scenes WHERE id = '".$url['4']."';");
        $row_scene = mysqli_fetch_assoc($query_scene);
        $query_lightstates = mysqli_query($con, 'SELECT * FROM lightstates WHERE scene_id = '.$row_scene['id'].';');
        while ($row_lightstates = mysqli_fetch_assoc($query_lightstates)) {
            $lightstates_array[$row_lightstates['light_id']] = array(
                'on' => (bool) $row_lightstates['state'],
                'bri' => intval($row_lightstates['bri']),
                (($row_lightstates['xy'] != '') ? 'xy' : 'ct') => (($row_lightstates['xy'] != '') ? $row_lightstates['xy'] : intval($row_lightstates['ct'])),
            );
            if ($row_lightstates['transitiontime'] != '0') {
                $lightstates_array[$row_lightstates['light_id']]['transitiontime'] = (int) $row_lightstates['transitiontime'];
            }
            if ($row_lightstates['transitiontime'] != '0') {
                $lightstates_array[$row_lightstates['light_id']]['transitiontime'] = (int) $row_lightstates['transitiontime'];
            }
        }
        $output_array[$row_scene['id']] = array(
            'name' => $row_scene['name'],
            'owner' => $row_scene['owner'],
            'picture' => $row_scene['picture'],
            'lastupdated' => $row_scene['lastupdated_converted'],
            'recycle' => (bool) $row_scene['recycle'],
            'locked' => (bool) $row_scene['locked'],
            'version' => 2,
            'lights' => json_decode($row_scene['lights'], true),
            'lightstates' => $lightstates_array,
        );
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('SCENES PUT:'.json_encode($data));
    if ($url['5'] == 'lightstates') {
        $update_string = 'UPDATE lightstates SET ';
        foreach ($data as $key => $value) {
            $url_response = implode('/', array_slice($url, 3));
            $output_array[] = array(
                'success' => array(
                    '/'.$url_response.'/'.$key => (($key == 'xy') ? (string) json_encode($value) : $value),
                ),
            );
            if ($key == 'on') {
                $key = 'state';
            }
            if (is_array($value)) {
                $value = json_encode($value);
            }
            $update_string .= $key." = '".$value."',";
        }
        $update_string = rtrim($update_string, ',');
        $update_string .= ' WHERE light_id  = '.$url['6'].' AND '.'scene_id = '.$url['4'];
        error_log($update_string);
        $update_lightstates = mysqli_query($con, $update_string);
    } else {
        $update_string = 'UPDATE scenes SET ';
        foreach ($data as $key => $value) {
            $url_response = implode('/', array_slice($url, 3));
            $output_array[] = array(
                'success' => array(
                    '/'.$url_response.'/'.$key => (($key == 'xy') ? (string) json_encode($value) : $value),
                ),
            );
            if (is_array($value)) {
                $value = json_encode($value);
            }
            if ($key == 'on') {
                $key = 'state';
            }
            $update_string .= $key." = '".$value."',";
        }
        $update_string = rtrim($update_string, ',');
        $update_string .= ' WHERE id = '.$url['4'];
        $update_scenes = mysqli_query($con, $update_string);
        error_log($update_string);
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('SCENES POST: '.json_encode($data));
    error_log("INSERT INTO `scenes`(`name`, `owner`, `picture`, `lastupdated`, `recycle`, `locked`, `appdata`, `lights`) VALUES ('".$data['name']."', '".$url['2']."', '', '".gmdate('Y-m-d H:i:s')."',". ((isset($data['recycle'])) ? (int) $data['recycle']:0).", 0, '".((isset($data['appdata'])) ? json_encode($data['appdata']) : '')."','".json_encode($data['lights'])."');");
    mysqli_query($con, "INSERT INTO `scenes`(`name`, `owner`, `picture`, `lastupdated`, `recycle`, `locked`, `appdata`, `lights`) VALUES ('".$data['name']."', '".$url['2']."', '', '".gmdate('Y-m-d H:i:s')."',". ((isset($data['recycle'])) ? (int) $data['recycle']:0).", 0, '".((isset($data['appdata'])) ? json_encode($data['appdata']) : '')."','".json_encode($data['lights'])."');");
    $inserted_scene_id = mysqli_insert_id($con);
    foreach ($data['lights'] as $light) {
        error_log("INSERT INTO `lightstates`(`light_id`, `scene_id`) VALUES ('".$light."', '".$inserted_scene_id.');');
        mysqli_query($con, 'INSERT INTO `lightstates`(`light_id`, `scene_id`) VALUES ('.$light.', '.$inserted_scene_id.');');
    }
    $output_array[] = array(
        'success' => array(
            'id' => (string) $inserted_scene_id,
        ),
    );
} elseif ($_SERVER['REQUEST_METHOD'] == 'DELETE') {
    error_log('scenes delete');
    mysqli_query($con, 'DELETE FROM `scenes` WHERE id = '.$url['4'].';');
    $output_array[] = array(
        'success' => '/scenes/'.$url['4'].' deleted',
    );
}
