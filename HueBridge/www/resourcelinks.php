<?php

if ($_SERVER['REQUEST_METHOD'] == 'GET') {
    if (!isset($url['4'])) {
        $query_resourcelinks = mysqli_query($con, 'SELECT * FROM resourcelinks;');
        while ($row_resourcelinks = mysqli_fetch_assoc($query_resourcelinks)) {
            $resourcelinks_array[$row_resourcelinks['id']] = array(
                  'name' => $row_resourcelinks['name'],
                  'description' => $row_resourcelinks['description'],
                  'type' => "Link",
                  'class' => (int) $row_resourcelinks['classid'],
                  'owner' => $row_resourcelinks['owner'],
                  'recycle' => (bool) $row_resourcelinks['recycle'],
                  'links' => json_decode($row_resourcelinks['links'], true),
              );
        }
        if (isset($resourcelinks_array)) {
            $output_array = $resourcelinks_array;
        } else {
            $output_array = new stdClass();
        }
    } elseif (is_numeric($url['4'])) {
        $query_resourcelinks = mysqli_query($con, "SELECT * FROM resourcelinks WHERE id = '".$url['4']."';");
        $row_resourcelinks = mysqli_fetch_assoc($query_resourcelinks);
        $output_array = array(
          'name' => $row_resourcelinks['name'],
          'description' => $row_resourcelinks['description'],
          'type' => "Link",
          'class' => (int) $row_resourcelinks['classid'],
          'owner' => $row_resourcelinks['owner'],
          'recycle' => (bool) $row_resourcelinks['recycle'],
          'links' => json_decode($row_resourcelinks['links'], true),
      );
    }
} elseif ($_SERVER['REQUEST_METHOD'] == 'PUT') {
    $data = json_decode(file_get_contents('php://input'), false);
    error_log(json_encode($data));
    $update_string = 'UPDATE resourcelinks SET ';
    foreach ($data as $key => $value) {
        $url_response = implode('/', array_slice($url, 3));
        $output_array[] = array(
            'success' => array(
                '/'.$url_response.'/'.$key => $value,
            ),
        );
        if (is_array($value)) {
            $value = json_encode($value);
        }
        error_log($key.'|'.$value);
        $update_string .= $key." = '".$value."',";
    }
    $update_string = rtrim($update_string, ',');
    $update_string .= ' WHERE id = '.$url['4'];
    $update_resourcelinks = mysqli_query($con, $update_string);
    error_log($update_string);
    echo json_encode($output_array, JSON_UNESCAPED_SLASHES);
    error_log('RESOURCELINKS PUT'.json_encode($output_array, JSON_UNESCAPED_SLASHES));
    exit(0);
} elseif ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    error_log('RESOURCELINKS POST:'.json_encode($data));
    mysqli_query($con, "INSERT INTO `resourcelinks`(`name`, `description`, `classid`, `owner`, `recycle`, `links`) VALUES ('".$data['name']."','".$data['description']."','".$data['classid']."','".$url['2']."','".$data['recycle']."','".json_encode($data['links'], true)."');");
    $output_array[] = array(
        'success' => array(
            'id' => (string) mysqli_insert_id($con),
        ),
    );
}
