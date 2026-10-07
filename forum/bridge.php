<?php
/** Machine-only, signed, loopback endpoint. Uses SMF's own post functions. */
$raw=file_get_contents('php://input');
$cfg=json_decode(file_get_contents(getenv('LISP_COMMUNITY_CONFIG')?:'/etc/lisp/community/settings.json'),true);
if (($_SERVER['REMOTE_ADDR']??'')!=='127.0.0.1' || $_SERVER['REQUEST_METHOD']!=='POST' || strlen($raw)>10485760 || !hash_equals(hash_hmac('sha256',$raw,$cfg['forumSecret']),$_SERVER['HTTP_X_LISP_SIGNATURE']??'')) { http_response_code(403); exit; }
$data=json_decode($raw,true);
if (!$data || !preg_match('/^[A-Za-z0-9:_-]{1,100}$/',$data['key']??'')) {http_response_code(400);exit;}
define('LISP_BRIDGE',true);
$_SERVER['HTTP_HOST']=$cfg['host']; $_SERVER['HTTPS']='on';
$ssi_guest_access=true;
$root=$cfg['forumDir']??'/opt/lisp-forum';
require $root.'/SSI.php';
require_once $root.'/Sources/Lisp.php';
require_once $root.'/Sources/Subs-Post.php';
$db=$db_connection; $key=$data['key'];
function lisp_bridge_query($sql,$params=[]) {
    global $db;
    $result=pg_query_params($db,$sql,$params);
    if (!$result) throw new RuntimeException('Bridge database operation failed');
    return $result;
}
try {
    lisp_bridge_query('BEGIN');
    lisp_bridge_query('SELECT pg_advisory_xact_lock(hashtext($1))',[$key]);
    $thread=pg_fetch_assoc(lisp_bridge_query('SELECT topic,message FROM lisp_threads WHERE key=$1',[$key]));
    $board=(int)pg_fetch_result(lisp_bridge_query("SELECT id_board FROM smf_boards WHERE name='Tournaments' ORDER BY id_board LIMIT 1"),0,0);
    if (!$board) throw new RuntimeException('Missing Tournament board');
    $poster=['id'=>500001,'name'=>'LISP','email'=>'tournaments@lan.invalid','ip'=>'127.0.0.1','update_post_count'=>true];
    $msg=['subject'=>$data['subject'],'body'=>$data['body'],'icon'=>'xx','smileys_enabled'=>false,'send_notifications'=>false,'approved'=>1];
    $topic=['id'=>$thread?(int)$thread['topic']:0,'board'=>$board];
    $event=$data['event']??null;
    if ($thread && !$event) {
        $msg['id']=(int)$thread['message'];
        if (!modifyPost($msg,$topic,$poster)) throw new RuntimeException('Forum update failed');
    } elseif (!$thread) {
        if (!createPost($msg,$topic,$poster)) throw new RuntimeException('Forum post failed');
        lisp_bridge_query('INSERT INTO lisp_threads VALUES($1,$2,$3)',[$key,$topic['id'],$msg['id']]);
        $thread=['topic'=>$topic['id'],'message'=>$msg['id']];
        if ($event) lisp_bridge_query('INSERT INTO lisp_events VALUES($1,$2,$3)',[$key,$event,$msg['id']]);
    } else {
        $q=lisp_bridge_query('SELECT message FROM lisp_events WHERE key=$1 AND event=$2',[$key,$event]);
        if (!pg_num_rows($q)) {
            if (!createPost($msg,$topic,$poster)) throw new RuntimeException('Forum result failed');
            lisp_bridge_query('INSERT INTO lisp_events VALUES($1,$2,$3)',[$key,$event,$msg['id']]);
        }
    }
    lisp_bridge_query('COMMIT');
    header('Content-Type: application/json');echo json_encode(['topic'=>(int)$thread['topic']]);
} catch (Throwable $e) {
    pg_query($db,'ROLLBACK');
    error_log('LISP forum publication failed: '.get_class($e));http_response_code(503);header('Content-Type: application/json');echo '{"error":"Forum update delayed"}';
}
