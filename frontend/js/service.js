// Everything the views need from "the backend", from either the real API or the in-browser demo.
import { CONFIG } from './config.js';

export const svc = await import(CONFIG.mock ? './mock.js' : './remote.js');
