<?php
/** Run on the LAN host: php tests/test_forum_runtime.php */
define('SMF', 1);
set_error_handler(function($severity, $message) { throw new ErrorException($message, 0, $severity); }, E_WARNING | E_NOTICE);
require '/opt/lisp-forum/Sources/Session.php';
$row = false;
$smcFunc = [
    'db_query' => function() { return true; },
    'db_fetch_row' => function() use (&$row) { return $row; },
    'db_free_result' => function() {},
];
$handler = new SmfSessionHandler();
if ($handler->read(str_repeat('a', 32)) !== '') throw new RuntimeException('Missing session was not empty');
$row = ['stored-session'];
if ($handler->read(str_repeat('a', 32)) !== 'stored-session') throw new RuntimeException('Existing session changed');
if ($handler->read('invalid') !== '') throw new RuntimeException('Invalid session ID accepted');
// Exercise the installed last-visit assignment with both PostgreSQL results.
$source = file_get_contents('/opt/lisp-forum/Sources/Load.php');
if (!preg_match('/list \(\$visitTime\) = [^;]+;/', $source, $matches)) throw new RuntimeException('Last-visit assignment not found');
foreach ([false, [123]] as $row) {
    $result = true;
    eval($matches[0]);
    if ($visitTime !== ($row === false ? null : 123)) throw new RuntimeException('Last-visit result changed');
}
// Exercise the installed signature preview with a real member-context array.
$source = file_get_contents('/opt/lisp-forum/Sources/Profile-Modify.php');
if (!preg_match('/\$context\[\x27member\x27\]\[\x27signature_preview\x27\] = parse_bbc\([^;]+;/', $source, $matches)) throw new RuntimeException('Signature preview not found');
function parse_bbc($text, $smileys, $cache_id, $tags) {
    if ($cache_id !== 'sig1') throw new RuntimeException('Wrong signature cache identity');
    return $text;
}
function get_signature_allowed_bbc_tags() { return []; }
$context = ['id_member' => 1, 'member' => []];
$memberContext = [1 => ['name' => 'Validation member']];
$signature = 'Signature preview';
eval($matches[0]);
if ($context['member']['signature_preview'] !== $signature) throw new RuntimeException('Signature preview changed');
// Preserve both permission groups and tolerate PostgreSQL's false at EOF.
$source = file_get_contents('/opt/lisp-forum/Sources/tasks/CreatePost-Notify.php');
if (!preg_match('/while \(\$permission_row = [^\n]+\)\s*\{\s*list [^\n]+;\s*\$group_permissions[^\n]+;\s*\}/', $source, $matches)) throw new RuntimeException('Notification permission loop not found');
foreach ([[], [[-1, '0']], [[0, '1']], [[-1, '0'], [0, '1'], [2, '0']]] as $permission_rows) {
    $request = true;
    $group_permissions = ['allowed' => [], 'denied' => []];
    $smcFunc['db_fetch_row'] = function() use (&$permission_rows) { return array_shift($permission_rows) ?: false; };
    $expected = ['allowed' => [], 'denied' => []];
    foreach ($permission_rows as $permission) $expected[$permission[1] === '0' ? 'allowed' : 'denied'][] = $permission[0];
    eval($matches[0]);
    if ($group_permissions !== $expected) throw new RuntimeException('Board notification permissions changed');
}
echo "PASS sessions, last visits, signature preview and empty/populated notification permissions without warnings.\n";
