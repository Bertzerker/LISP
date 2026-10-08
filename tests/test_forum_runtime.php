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
echo "PASS missing/existing/invalid sessions and missing/existing last-visit rows without warnings.\n";
