<?php
/** Machine-only, signed, loopback endpoint. Uses SMF's own post functions. */
$raw=file_get_contents('php://input');
$cfg=json_decode(file_get_contents(getenv('LISP_COMMUNITY_CONFIG')?:'/etc/lisp/community/settings.json'),true);
if (($_SERVER['REMOTE_ADDR']??'')!=='127.0.0.1' || $_SERVER['REQUEST_METHOD']!=='POST' || strlen($raw)>10485760 || !hash_equals(hash_hmac('sha256',$raw,$cfg['forumSecret']),$_SERVER['HTTP_X_LISP_SIGNATURE']??'')) { http_response_code(403); exit; }
$data=json_decode($raw,true);
if (!$data || !preg_match('/^[A-Za-z0-9:_-]{1,100}$/',$data['key']??'')) {http_response_code(400);exit;}
if (($data['operation']??'')==='status') {
    $actor=$data['user']??[];
    if (!is_int($actor['id']??null) || $actor['id']<1 || !preg_match('/^[A-Za-z][A-Za-z0-9_-]{1,19}$/',$actor['name']??'') || !in_array($actor['role']??'', ['player','admin'],true)) {http_response_code(400);exit;}
    $GLOBALS['lisp_bridge_actor']=$actor;
}
define('LISP_BRIDGE',true);
$_SERVER['HTTP_HOST']=$cfg['host']; $_SERVER['HTTPS']='on';
$ssi_guest_access=true;
$root=$cfg['forumDir']??'/opt/lisp-forum';
require $root.'/SSI.php';
require_once $root.'/Sources/Lisp.php';
require_once $root.'/Sources/Subs-Post.php';
if (($data['operation']??'')==='status') {
    try {
        $member=(int)$actor['id'];
        $q=$smcFunc['db_query']('', 'SELECT COUNT(*) FROM {db_prefix}pm_recipients WHERE id_member={int:member} AND deleted=0 AND (is_read & 1)=0', ['member'=>$member]);
        $messages=(int)$smcFunc['db_fetch_row']($q)[0];$smcFunc['db_free_result']($q);
        $q=$smcFunc['db_query']('', 'SELECT COUNT(*) FROM {db_prefix}topics AS t INNER JOIN {db_prefix}boards AS b ON b.id_board=t.id_board LEFT JOIN {db_prefix}log_topics AS lt ON lt.id_topic=t.id_topic AND lt.id_member={int:member} LEFT JOIN {db_prefix}log_mark_read AS lmr ON lmr.id_board=t.id_board AND lmr.id_member={int:member} WHERE {query_wanna_see_board} AND t.approved=1 AND COALESCE(lt.unwatched,0)=0 AND t.id_last_msg>COALESCE(lt.id_msg,0) AND t.id_last_msg>COALESCE(lmr.id_msg,0)', ['member'=>$member]);
        $topics=(int)$smcFunc['db_fetch_row']($q)[0];$smcFunc['db_free_result']($q);
        $q=$smcFunc['db_query']('', 'SELECT filename,attachment_type,id_attach FROM {db_prefix}attachments WHERE id_member={int:member} AND id_msg=0 ORDER BY id_attach DESC LIMIT 1', ['member'=>$member]);
        $pic=$smcFunc['db_fetch_assoc']($q);$smcFunc['db_free_result']($q);$avatar=null;
        if ($pic && (int)$pic['attachment_type']===1 && preg_match('/^[A-Za-z0-9_.-]+\.(png|gif|jpe?g|webp|svg)$/i',$pic['filename'])) $avatar='/forum/custom_avatar/'.rawurlencode($pic['filename']);
        elseif ($pic && (int)$pic['attachment_type']===0) $avatar='/forum/index.php?action=dlattach;attach='.(int)$pic['id_attach'].';type=avatar';
        header('Content-Type: application/json');header('Cache-Control: no-store');echo json_encode(['avatar'=>$avatar,'unreadMessages'=>$messages,'unreadTopics'=>$topics]);exit;
    } catch (Throwable $e) {http_response_code(503);header('Content-Type: application/json');echo '{"error":"Forum status unavailable"}';exit;}
}
if (($data['operation']??'')==='avatars') {
    $ids=$data['users']??null;
    if (!is_array($ids) || count($ids)>200 || array_filter($ids,fn($id)=>!is_int($id)||$id<1)) {http_response_code(400);exit;}
    try {
        $avatars=[];
        if ($ids) {
            $q=$smcFunc['db_query']('', 'SELECT id_member,filename,attachment_type,id_attach FROM {db_prefix}attachments WHERE id_member IN ({array_int:members}) AND id_msg=0 ORDER BY id_attach DESC', ['members'=>$ids]);
            while ($pic=$smcFunc['db_fetch_assoc']($q)) {
                $id=(int)$pic['id_member'];
                if (array_key_exists($id,$avatars)) continue;
                $avatars[$id]=null;
                if ((int)$pic['attachment_type']===1 && preg_match('/^[A-Za-z0-9_.-]+\.(png|gif|jpe?g|webp|svg)$/i',$pic['filename'])) $avatars[$id]='/forum/custom_avatar/'.rawurlencode($pic['filename']);
                elseif ((int)$pic['attachment_type']===0) $avatars[$id]='/forum/index.php?action=dlattach;attach='.(int)$pic['id_attach'].';type=avatar';
            }
            $smcFunc['db_free_result']($q);
        }
        header('Content-Type: application/json');header('Cache-Control: no-store');echo json_encode(['avatars'=>(object)$avatars]);exit;
    } catch (Throwable $e) {http_response_code(503);header('Content-Type: application/json');echo '{"error":"Avatars unavailable"}';exit;}
}
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
