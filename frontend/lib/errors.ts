/**
 * The API's error envelope, read once, in one place.
 *
 * `message` is shown verbatim (SPEC-0010 C3). The only text this module owns is
 * the one the API cannot give: a 5xx or no answer at all (AC-0010-42).
 */

export const GENERIC_FAILURE = "Não foi possível concluir. Tente novamente em instantes.";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;
  readonly correlationId: string | null;
  readonly retryAfter: number | null;

  constructor(options: {
    status: number;
    code: string;
    message: string;
    fields?: Record<string, string>;
    correlationId?: string | null;
    retryAfter?: number | null;
  }) {
    super(options.message);
    this.status = options.status;
    this.code = options.code;
    this.fields = options.fields ?? {};
    this.correlationId = options.correlationId ?? null;
    this.retryAfter = options.retryAfter ?? null;
  }

  /** Whether the API explained itself, or this is the generic failure. */
  get isGeneric(): boolean {
    return this.code === "UNAVAILABLE";
  }
}

interface Envelope {
  error?: {
    code?: string;
    message?: string;
    fields?: Record<string, string>;
    correlation_id?: string;
  };
}

export async function readError(response: Response): Promise<ApiError> {
  const correlationId = response.headers.get("x-correlation-id");
  const retryAfterHeader = response.headers.get("retry-after");
  const retryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : null;

  if (response.status < 500) {
    try {
      const body = (await response.json()) as Envelope;
      if (body.error?.code && body.error.message) {
        return new ApiError({
          status: response.status,
          code: body.error.code,
          message: body.error.message,
          fields: body.error.fields,
          correlationId: body.error.correlation_id ?? correlationId,
          retryAfter: Number.isNaN(retryAfter) ? null : retryAfter,
        });
      }
    } catch {
      // Not the envelope: fall through to the generic failure.
    }
  }

  let bodyCorrelation: string | null = null;
  try {
    bodyCorrelation = ((await response.clone().json()) as Envelope).error?.correlation_id ?? null;
  } catch {
    bodyCorrelation = null;
  }
  return unavailable(bodyCorrelation ?? correlationId);
}

export function unavailable(correlationId: string | null = null): ApiError {
  return new ApiError({
    status: 0,
    code: "UNAVAILABLE",
    message: GENERIC_FAILURE,
    correlationId,
  });
}
