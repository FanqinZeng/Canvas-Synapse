# References and third-party notices

Canvas Synapse's workspace UI, storage, retrieval and model adapters are newly implemented.

The SJTU connector protocol and data-field mappings in `synapse/canvas.py` were adapted with reference to [ZHS-XER/CanvasKit](https://github.com/ZHS-XER/CanvasKit), specifically `src/canvaskit/video.py` and `src/canvaskit/canvas.py`. The applicable notice is reproduced below.

## CanvasKit — MIT License

Copyright (c) 2026 ZHS-XER

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Design and architecture references

- [SJTU Canvas Helper](https://github.com/Okabe-Rintarou-0/SJTU-Canvas-Helper): platform compatibility and timestamped classroom material organization.
- [BiliNote](https://github.com/JefferyHcool/BiliNote): video-note and original-evidence question answering workflow.
- [Canvas2Note](https://github.com/HashBrowns-fries/SJTU_Canvas2Note): end-to-end course-note workflow reference. No code copied.
- [OpenAI official documentation](https://developers.openai.com/api/docs/guides/text): Responses API integration.
- [智谱官方文档](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction): OpenAI-compatible GLM integration.

No third-party JavaScript, fonts, runtime packages, model weights or course media are bundled. Demonstration slides and transcript are synthetic examples created for this project, not recordings of an actual class.
