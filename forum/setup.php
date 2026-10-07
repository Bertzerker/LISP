<?php
/** One-time, CLI-only migration from a private, credential-free legacy export. */
if (PHP_SAPI !== 'cli') {http_response_code(403);exit;}
$export=json_decode(file_get_contents($argv[1]),true,512,JSON_THROW_ON_ERROR);
$cfg=json_decode(file_get_contents(getenv('LISP_COMMUNITY_CONFIG')?:'/etc/lisp/community/settings.json'),true);
$root=$cfg['forumDir']??'/opt/lisp-forum';
$pdo=new PDO('pgsql:host=127.0.0.1;port=5433;dbname='.($cfg['forumDatabase']??'lisp_forum'),'lisp_forum',$cfg['forumPassword'],[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
$pdo->exec('CREATE TABLE IF NOT EXISTS lisp_threads(key TEXT PRIMARY KEY,topic INTEGER NOT NULL,message INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS lisp_events(key TEXT,event TEXT,message INTEGER NOT NULL,PRIMARY KEY(key,event)); CREATE TABLE IF NOT EXISTS lisp_migration(key TEXT PRIMARY KEY,value TEXT)');
$hooks=['integrate_pre_include'=>'/opt/lisp-forum/Sources/Lisp.php','integrate_verify_user'=>'lisp_verify_user','integrate_verify_password'=>'lisp_verify_password','integrate_actions'=>'lisp_actions','integrate_profile_areas'=>'lisp_profile_areas','integrate_load_theme'=>'lisp_theme','registration_method'=>'3','send_welcomeEmail'=>'0','mail_queue'=>'0','enableCompressedOutput'=>'0','jquery_source'=>'local','global_character_set'=>'UTF-8','enableVBStyleLogin'=>'0','cache_enable'=>'0','requireAgreement'=>'0','requirePolicyAgreement'=>'0','enableReportPM'=>'0'];
$hooks['integrate_pre_include']=$root.'/Sources/Lisp.php';
$q=$pdo->prepare('INSERT INTO smf_settings(variable,value) VALUES(?,?) ON CONFLICT(variable) DO UPDATE SET value=excluded.value');
foreach($hooks as $key=>$value)$q->execute([$key,$value]);
$q=$pdo->prepare("INSERT INTO smf_members(id_member,member_name,real_name,email_address,passwd,password_salt,id_group,date_registered,buddy_list,signature,ignore_boards) VALUES(500001,'LISP','Tournament Bot','tournaments@lan.invalid',?,?,0,?,'','','') ON CONFLICT(id_member) DO NOTHING");
$q->execute([password_hash(bin2hex(random_bytes(32)),PASSWORD_BCRYPT),bin2hex(random_bytes(16)),time()]);
define('LISP_BRIDGE',true);$_SERVER['HTTP_HOST']=$cfg['host'];$_SERVER['REMOTE_ADDR']='127.0.0.1';$_SERVER['HTTPS']='on';$_SERVER['SCRIPT_NAME']='/forum/index.php';$_SERVER['REQUEST_URI']='/forum/index.php';$ssi_guest_access=true;
require $root.'/SSI.php';require_once $root.'/Sources/Lisp.php';require_once $root.'/Sources/Subs-Post.php';
foreach($export['users'] as $user)lisp_member($user);
if (!$pdo->query("SELECT value FROM lisp_migration WHERE key='legacy-complete'")->fetchColumn()) {
    // Public forum cutover has not happened. Only the stock welcome fixture is discarded.
    if ($pdo->query('SELECT count(*) FROM smf_topics')->fetchColumn()>1) throw new RuntimeException('Forum is not empty; refusing to erase live topics');
    pg_query($db_connection,'BEGIN');
    try {
        pg_query($db_connection,'DELETE FROM smf_messages; DELETE FROM smf_topics; DELETE FROM smf_boards; UPDATE smf_members SET posts=0;');
        foreach($export['boards'] as $b) {
            pg_query_params($db_connection,"INSERT INTO smf_boards(id_board,id_cat,board_order,name,description,member_groups) VALUES($1,1,$1,$2,'LAN community discussion','0')",[$b['id'],$b['name']]);
        }
        pg_query_params($db_connection,"INSERT INTO smf_boards(id_board,id_cat,board_order,name,description,member_groups) VALUES(6,1,6,'Tournaments','Game votes, brackets and tournament results','0')",[]);
        foreach($export['topics'] as $t) {
            $topic=['id'=>0,'board'=>(int)$t['board']];
            foreach($export['posts'] as $p)if($p['topic']===$t['id']) {
                $user=$export['members'][(string)$p['user_id']];
                $msg=['subject'=>htmlspecialchars($t['title'],ENT_QUOTES,'UTF-8'),'body'=>str_replace(['[',']'],['&#91;','&#93;'],htmlspecialchars($p['body'],ENT_QUOTES,'UTF-8')),'poster_time'=>(int)$p['created'],'smileys_enabled'=>false,'send_notifications'=>false,'icon'=>'xx'];
                $poster=['id'=>(int)$user['id'],'name'=>$user['name'],'email'=>'lisp-'.$user['id'].'@lan.invalid','ip'=>'127.0.0.1','update_post_count'=>true];
                if (!createPost($msg,$topic,$poster))throw new RuntimeException('Legacy post migration failed');
                if (!pg_query_params($db_connection,'INSERT INTO lisp_migration VALUES($1,$2)', ['post:'.$p['id'],(string)$msg['id']]))throw new RuntimeException('Migration map failed');
            }
            if ($topic['id']) {
                pg_query_params($db_connection,'UPDATE smf_topics SET locked=$1 WHERE id_topic=$2',[(int)$t['locked'],$topic['id']]);
                pg_query_params($db_connection,'INSERT INTO lisp_migration VALUES($1,$2)',['topic:'.$t['id'],(string)$topic['id']]);
            }
        }
        pg_query($db_connection,"SELECT setval('smf_boards_seq',6,true); INSERT INTO lisp_migration VALUES('legacy-complete','1'); COMMIT;");
    } catch(Throwable $e) {pg_query($db_connection,'ROLLBACK');throw $e;}
}
$pdo->exec("SELECT setval('smf_members_seq',500001,true)");
updateSettings(['totalMembers'=>$pdo->query('SELECT count(*) FROM smf_members')->fetchColumn(),'latestMember'=>500001,'latestRealName'=>'Tournament Bot','totalMessages'=>$pdo->query('SELECT count(*) FROM smf_messages')->fetchColumn(),'totalTopics'=>$pdo->query('SELECT count(*) FROM smf_topics')->fetchColumn()]);
echo json_encode(['boards'=>(int)$pdo->query('SELECT count(*) FROM smf_boards')->fetchColumn(),'topics'=>(int)$pdo->query('SELECT count(*) FROM smf_topics')->fetchColumn(),'posts'=>(int)$pdo->query('SELECT count(*) FROM smf_messages')->fetchColumn(),'members'=>(int)$pdo->query('SELECT count(*) FROM smf_members')->fetchColumn()])."\n";
