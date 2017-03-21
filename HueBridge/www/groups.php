<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_groups = mysqli_query($con, 'SELECT * FROM groups;');
        while ($row_groups = mysqli_fetch_assoc($query_groups)) {
            $query_lights_status             = mysqli_query($con, 'SELECT COUNT(*), SUM(state), bri, hue, sat, effect, xy, ct, alert, colormode FROM lights WHERE `id` IN (' . implode(',', array_map('intval', json_decode($row_groups['lights']))) . ') LIMIT 1;');
            $row_lights_status               = mysqli_fetch_assoc($query_lights_status);
            $groups_array[$row_groups['id']] = array(
                'action' => array(
                    'on' => (($row_lights_status['SUM(state)'] > 0) ? true : false),
                    'bri' => (int) $row_lights_status['bri'],
                    'hue' => (int) $row_lights_status['hue'],
                    'sat' => (int) $row_lights_status['sat'],
                    'effect' => $row_lights_status['effect'],
                    'xy' => json_decode($row_lights_status['xy'], true),
                    'ct' => (int) $row_lights_status['ct'],
                    'alert' => $row_lights_status['alert'],
                    'colormode' => $row_lights_status['colormode']
                ),
                'lights' => json_decode($row_groups['lights'], true),
                'name' => $row_groups['name'],
                'type' => $row_groups['type'],
                'class' => $row_groups['class'],
                'state' => array(
                    'any_on' => (($row_lights_status['SUM(state)'] == '0') ? false : true),
                    'all_on' => (($row_lights_status['COUNT(*)'] == $row_lights_status['SUM(state)']) ? true : false)
                )
            );
        }
        if (isset($groups_array)) {
            if ($print_entire_config) {
                $output_array['groups'] = $groups_array;
            } else {
                $output_array = $groups_array;
            }
        } else {
            if ($print_entire_config) {
                $output_array['groups'] = new stdClass();
            } else {
                $output_array = new stdClass();
            }
        }
    } elseif (is_numeric($url['4'])) {
        $query_group         = mysqli_query($con, "SELECT * FROM groups WHERE id = '" . $url['4'] . "';");
        $row_group           = mysqli_fetch_assoc($query_group);
        $query_lights_status = mysqli_query($con, 'SELECT COUNT(*), SUM(state), bri, hue, sat, effect, xy, ct, alert, colormode FROM lights WHERE `id` IN (' . implode(',', array_map('intval', json_decode($row_group['lights']))) . ') LIMIT 1;');
        $row_lights_status   = mysqli_fetch_assoc($query_lights_status);
        $output_array        = array(
            'action' => array(
                'on' => (($row_lights_status['SUM(state)'] > 0) ? true : false),
                'bri' => (int) $row_lights_status['bri'],
                'hue' => (int) $row_lights_status['hue'],
                'sat' => (int) $row_lights_status['sat'],
                'effect' => $row_lights_status['effect'],
                'xy' => json_decode($row_lights_status['xy'], true),
                'ct' => (int) $row_lights_status['ct'],
                'alert' => $row_lights_status['alert'],
                'colormode' => $row_lights_status['colormode']
            ),
            'lights' => json_decode($row_group['lights'], true),
            'name' => $row_group['name'],
            'type' => $row_group['type'],
            'class' => $row_grous['class'],
            'state' => array(
                'any_on' => (($row_lights_status['SUM(state)'] == '0') ? false : true),
                'all_on' => (($row_lights_status['COUNT(*)'] == $row_lights_status['SUM(state)']) ? true : false)
            )
        );
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), true);
    foreach ($data as $key => $value) {
        $url_response   = implode('/', array_slice($url, 3));
        $output_array[] = array(
            'success' => array(
                '/' . $url_response . '/' . $key => $value
            )
        );
        error_log('GROUP PUT:' . json_encode($data, JSON_UNESCAPED_SLASHES));
    }
    if (isset($data['scene'])) {
        $query_scene = mysqli_query($con, 'SELECT * FROM lightstates WHERE scene_id = ' . $data['scene'] . ';');
        while ($row_scene = mysqli_fetch_assoc($query_scene)) {
            $curl_arguments['bri'] = $row_scene['bri'];
            $update_string         = 'UPDATE lights SET ';
            if ($row_scene['xy'] != '') {
                $update_string_actions = 'state = ' . (int) $row_scene['state'] . ', bri = ' . $row_scene['bri'] . ", xy = '" . $row_scene['xy'] . "', colormode = 'xy' ";
                $curl_arguments['xy']  = json_decode($row_scene['xy'], true);
            } else {
                $update_string_actions = 'state = ' . (int) $row_scene['state'] . ', bri = ' . $row_scene['bri'] . ', ct = ' . $row_scene['ct'] . ", colormode = 'ct' ";
                $curl_arguments['ct']  = $row_scene['ct'];
            }
            $update_string .= $update_string_actions . 'WHERE id = ' . $row_scene['light_id'] . ';';
            if ($row_scene['transitiontime'] != '0') {
                $curl_arguments['transitiontime'] = $row_scene['transitiontime'];
            }
            error_log('light_json:' . json_encode($curl_arguments));
            update_light($row_scene['light_id'], json_encode($curl_arguments));
            error_log('query:' . $update_string);
            mysqli_query($con, $update_string);
        }
    } elseif (isset($data['on'])) {
        if ($url['4'] == '0') {
            $query_all_lights = mysqli_query($con, 'SELECT id FROM lights;');
            while ($row_all_lights = mysqli_fetch_assoc($query_all_lights)) {
                update_light($row_all_lights['id'], json_encode($data));
            }
            mysqli_query($con, 'UPDATE lights set state = ' . (int) $data['on'] . ';');
        } else {
            $query_lights = mysqli_query($con, 'SELECT lights FROM groups WHERE id = ' . $url['4'] . ';');
            $row_lights   = mysqli_fetch_assoc($query_lights);
            error_log('group on :' . $row_lights['lights']);
            foreach (json_decode($row_lights['lights']) as $light) {
                update_light($light, json_encode($data));
                mysqli_query($con, 'UPDATE lights set state = ' . (int) $data['on'] . ' WHERE id = ' . $light . ';');
            }
        }
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('GROUP POST:' . json_encode($data));
    mysqli_query($con, "INSERT INTO `groups`(`lights`, `name`, `type`, `class`) VALUES ('" . json_encode($data['lights']) . "','" . $data['name'] . "','" . $data['type'] . "','" . $data['class'] . "');");
    $output_array[] = array(
        'success' => array(
            'id' => (string) mysqli_insert_id($con)
        )
    );
} elseif ($_SERVER['REQUEST_METHOD'] == 'DELETE') {
    mysqli_query($con, 'DELETE FROM `groups` WHERE id = ' . $url['4'] . ';');
    $output_array[] = array(
        'success' => '/groups/' . $url['4'] . ' deleted'
    );
    error_log('group delete');
}

