# Third-party notices

## Mumble widget

Upstream: https://github.com/alfg/mumble-widget
Reviewed revision: a6095753026684f6d7cde198c71bbe2c2812ee18 (v0.3.1).
Upstream declares MIT License, copyright Alfred Gutierrez, in its README.
`web/vendor/mumble-widget/mumble-widget.js` is a LISP adaptation of its channel
viewer/CVP approach. The rendering and fetching code was rewritten to use local
authenticated JSON, safe DOM methods, the portal palette, a remembered tab toggle
and native Join link. CDN/jQuery/Knockout/JSONP/eval dependencies are removed.
The MIT notice is retained below and beside the adapted file.

MIT License

Copyright (c) Alfred Gutierrez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## Runtime dependencies

Mumble Server and matching Ice schema are installed from the CachyOS/Arch
package repository. The official ZeroC `ice` npm package is pinned to 3.7.100,
installed on the host, and retains its own package license. Those third-party
runtime packages, generated bindings and binaries are not redistributed in the
LISP source archive. The project's bundled font notice is `style/Silkscreen-OFL.txt`.
