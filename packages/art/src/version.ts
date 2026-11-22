/**
 * The identity of the clean-room generator.
 *
 * These constants are emitted into every artefact's provenance record. They
 * change only when the generator changes in a way that alters its output.
 */

/** The generator's output format version. */
export const GENERATOR_VERSION = '1.0.0';

/** The name that appears in the provenance manifest. */
export const GENERATOR_NAME = '@swl/art';

/** The dedication applied to every file this package produces. */
export const LICENCE = 'CC0-1.0';

/**
 * The provenance statement attached to every entry. It is deliberately
 * specific: a vague "original" claim is worth very little, and a reader
 * should be able to tell exactly what was and was not used.
 */
export const ORIGINAL_WORK_STATEMENT =
  'Original work: drawn or synthesised from primitives by this generator. ' +
  'No file from the vendored upstream, the decompiled client, an atlas or a ' +
  'proprietary font was read, traced or copied.';

/** The notice shipped beside the files, so the dedication travels with them. */
export const CC0_NOTICE =
  'CC0 1.0 Universal\n' +
  '\n' +
  'To the extent possible under law, the contributors to Social Wars Legacy have\n' +
  'waived all copyright and related or neighbouring rights to the files in this\n' +
  'directory and to the generator that produced them.\n' +
  '\n' +
  'The full legal code is at <https://creativecommons.org/publicdomain/zero/1.0/legalcode>.\n' +
  'This dedication is not legal advice and carries no warranty.\n';
