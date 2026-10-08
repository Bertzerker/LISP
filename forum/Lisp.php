<?php
/** LISP account integration for pinned SMF 2.1. No human password is stored here. */
if (!defined('SMF')) die('No direct access');
function lisp_config() {
    static $config;
    if (!$config) $config = json_decode(file_get_contents(getenv('LISP_COMMUNITY_CONFIG')?:'/etc/lisp/community/settings.json'), true, 32, JSON_THROW_ON_ERROR);
    return $config;
}
function lisp_account_call($data) {
    $sock = stream_socket_client('unix://'.(getenv('LISP_ACCOUNT_SOCKET')?:'/run/lisp-accounts/auth.sock'), $errno, $message, 8);
    if (!$sock) throw new RuntimeException('Account service unavailable');
    stream_set_timeout($sock, 8); fwrite($sock, json_encode($data)."\n");
    $reply = fgets($sock, 65537); fclose($sock);
    $value = json_decode($reply ?: '{}', true);
    if (!$value || isset($value['error'])) throw new RuntimeException($value['error']??'Log in to the LAN portal');
    return $value;
}
function lisp_db() {
    static $db;
    if (!$db) {
        $cfg = lisp_config();
        $db = new PDO('pgsql:host=127.0.0.1;port=5433;dbname='.($cfg['forumDatabase']??'lisp_forum'), 'lisp_forum', $cfg['forumPassword'], [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
    }
    return $db;
}
function lisp_member($user) {
    $db = lisp_db();
    $q = $db->prepare('INSERT INTO smf_members (id_member,member_name,real_name,email_address,passwd,password_salt,id_group,date_registered,is_activated,buddy_list,signature,ignore_boards) VALUES (?,?,?,?,?,?,?,?,1,\'\',\'\',\'\') ON CONFLICT (id_member) DO UPDATE SET member_name=excluded.member_name,real_name=excluded.real_name,id_group=excluded.id_group,additional_groups=\'\'');
    $q->execute([(int)$user['id'], $user['name'], $user['name'], 'lisp-'.$user['id'].'@lan.invalid', password_hash(bin2hex(random_bytes(24)), PASSWORD_BCRYPT), bin2hex(random_bytes(16)), $user['role']==='admin'?1:0, (int)($user['created']??time())]);
    return (int)$user['id'];
}
function lisp_verify_user() {
    if (defined('LISP_BRIDGE')) return isset($GLOBALS['lisp_bridge_actor']) ? lisp_member($GLOBALS['lisp_bridge_actor']) : 500001;
    return lisp_member($GLOBALS['lisp_account']);
}
function lisp_verify_password($name, $password, $unused=false) {
    if (defined('LISP_BRIDGE')) return false;
    if (strcasecmp($name, $GLOBALS['lisp_account']['name']) !== 0) return false;
    try {
        $reply=lisp_account_call(['op'=>'verify-password', 'token'=>$_COOKIE['lisp_session']??'', 'ip'=>$_SERVER['REMOTE_ADDR'], 'password'=>$password]);
        return !empty($reply['verified']);
    } catch (Throwable $e) { return false; }
}
function lisp_actions(&$actions) {
    foreach (['login','login2','logout','register','register2','reminder','activate'] as $action) $actions[$action]=['','lisp_home'];
}
function lisp_home() { header('Location: /'); exit; }
function lisp_profile_areas(&$areas) {
    global $context;
    $areas['info']['areas']['trophies']=['label'=>'Trophies', 'function'=>'lisp_trophies', 'icon'=>'stats', 'permission'=>['own'=>'is_not_guest','any'=>'profile_view']];
    // The portal owns credentials, display names and roles.
    foreach ($areas as &$section) foreach (['account','deleteaccount','groupmembership'] as $key) unset($section['areas'][$key]);
    if (($_REQUEST['area']??'')==='account' || ($_REQUEST['area']??'')==='deleteaccount') lisp_home();
}
function lisp_trophies() {
    global $context;
    $cfg=lisp_config(); $id=(int)$context['id_member'];
    $opts=['http'=>['header'=>'X-LISP-Private: '.$cfg['forumSecret']."\r\n",'timeout'=>8]];
    $result=@file_get_contents(($cfg['communityUrl']??'http://127.0.0.1:8791').'/community-private/profile/'.$id,false,stream_context_create($opts));
    $context['lisp_profile']=$result?json_decode($result,true):['trophies'=>[]];
    $context['sub_template']='lisp_trophies'; $context['page_title']='Tournament trophies';
}
function template_lisp_trophies() {
    global $context;
    echo '<h3 class="catbg">Tournament trophies</h3><div class="windowbg"><p><a href="/trophies/?user=',(int)$context['id_member'],'">Open Trophy Room</a></p>';
    $awards=$context['lisp_profile']['trophies']??[];
    if (!$awards) echo '<p>No tournament trophies yet.</p>';
    foreach ($awards as $a) echo '<p><strong>', ['','Gold','Silver','Bronze'][(int)$a['rank']], '</strong> · <a href="/tournaments/?id=',(int)$a['poll'],'">',htmlspecialchars($a['name'], ENT_QUOTES, 'UTF-8'),'</a> · ',htmlspecialchars($a['gameName']??$a['game'], ENT_QUOTES, 'UTF-8'),'</p>';
    echo '</div>';
}
function lisp_editor_options(&$options) { $options['style']='/forum-editor.css'; }
function lisp_theme() {
    if (defined('LISP_BRIDGE')) return;
    global $context;
    add_integration_function('integrate_sceditor_options','lisp_editor_options',false);
    $context['html_headers'].='<link rel="stylesheet" href="/portal.css?v=20261008-personal"><link rel="stylesheet" href="/forum-portal.css?v=20261008"><script src="/auth.js" defer></script><script src="/shell.js?v=20261008-personal" defer></script>';
}
if (!defined('LISP_BRIDGE')) {
    try {
        $GLOBALS['lisp_account']=lisp_account_call(['op'=>'session','token'=>$_COOKIE['lisp_session']??'', 'ip'=>$_SERVER['REMOTE_ADDR']]);
        unset($_COOKIE['LISP_SMF']);
    } catch (Throwable $e) { error_log('LISP forum session unavailable: '.$e->getMessage()); http_response_code(401); echo 'Log in on the LAN portal home page.'; exit; }
}
