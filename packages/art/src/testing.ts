/** A filesystem double that records every path a command touches. */
import type { FileIO } from './io.ts';

export interface RecordedWrite {
  readonly path: string;
  readonly bytes: Uint8Array;
}

export interface RecordingIO {
  readonly io: FileIO;
  readonly reads: string[];
  readonly writes: RecordedWrite[];
  readonly directories: string[];
}

export function recordingIO(files: ReadonlyMap<string, Uint8Array> = new Map()): RecordingIO {
  const reads: string[] = [];
  const writes: RecordedWrite[] = [];
  const directories: string[] = [];
  return {
    reads,
    writes,
    directories,
    io: {
      async mkdir(directory) {
        directories.push(directory);
        return undefined;
      },
      async writeFile(file, data) {
        writes.push({ path: file, bytes: data });
      },
      async readFile(file) {
        reads.push(file);
        const found = files.get(file);
        if (!found) throw new Error(`no such file: ${file}`);
        return found;
      },
    },
  };
}
