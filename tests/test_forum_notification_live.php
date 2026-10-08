<?php
/** Actual installed task, native PostgreSQL queries, no notifications sent. */
define('LISP_BRIDGE', true);
$_SERVER['HTTP_HOST'] = '192.168.8.138';
$_SERVER['HTTPS'] = 'on';
$ssi_guest_access = true;
require '/opt/lisp-forum/SSI.php';
$cron_source = file_get_contents('/opt/lisp-forum/cron.php');
$start = strpos($cron_source, 'abstract class SMF_BackgroundTask');
if ($start === false) throw new RuntimeException('Native task base not found');
eval(preg_replace('/\?>\s*$/', '', substr($cron_source, $start)));
require '/opt/lisp-forum/Sources/tasks/CreatePost-Notify.php';
set_error_handler(function($severity,$message) { throw new ErrorException($message,0,$severity); }, E_WARNING | E_NOTICE);
// An edit without mentions/quotes exits after the actual permissions/watcher
// queries. It never creates alerts, mail, posts or changes subscriptions.
foreach ([1, 6] as $board) {
    $task = new CreatePost_Notify_Background([
        'msgOptions' => ['id' => 0, 'poster_time' => time(), 'quoted_members' => [], 'mentioned_members' => []],
        'topicOptions' => ['id' => 0, 'board' => $board],
        'posterOptions' => ['id' => 500001],
        'type' => 'edit',
    ]);
    if ($task->execute() !== true) throw new RuntimeException('Notification task failed');
}
echo "PASS actual installed notification task with native board permission queries and no outgoing notifications.\n";
