/**
 * The JVM's java.lang.Math speed, for tools/jmath_fuzz.py --bench (our notes only): nanoseconds per call over a fixed
 * array of inputs in the function's usual range, warmed up, as BATCHES timed passes.
 *
 *     java JmathBench FUNCTION
 *
 * Prints one JSON line: the median and the 99th percentile of the per-call time across the passes.
 */
public final class JmathBench {
    static final int INPUTS = 1 << 14, BATCHES = 400;
    static volatile double sink;

    static double run(String f, double[] x, double[] y) {
        double s = 0;
        switch (f) {
            case "sin": for (int i = 0; i < x.length; i++) s += Math.sin(x[i]); break;
            case "cos": for (int i = 0; i < x.length; i++) s += Math.cos(x[i]); break;
            case "tan": for (int i = 0; i < x.length; i++) s += Math.tan(x[i]); break;
            case "exp": for (int i = 0; i < x.length; i++) s += Math.exp(x[i]); break;
            case "log": for (int i = 0; i < x.length; i++) s += Math.log(x[i]); break;
            case "log10": for (int i = 0; i < x.length; i++) s += Math.log10(x[i]); break;
            case "pow": for (int i = 0; i < x.length; i++) s += Math.pow(x[i], y[i]); break;
            case "cbrt": for (int i = 0; i < x.length; i++) s += Math.cbrt(x[i]); break;
            case "atan2": for (int i = 0; i < x.length; i++) s += Math.atan2(x[i], y[i]); break;
            default: throw new IllegalArgumentException(f);
        }
        return s;
    }

    public static void main(String[] args) {
        String f = args[0];
        java.util.SplittableRandom r = new java.util.SplittableRandom(1);
        double[] x = new double[INPUTS], y = new double[INPUTS];
        for (int i = 0; i < INPUTS; i++) {
            double[] range = JmathFuzz.range(f);
            x[i] = range[0] + r.nextDouble() * (range[1] - range[0]);
            y[i] = f.equals("pow") ? -16 + 32 * r.nextDouble() : r.nextDouble() * 8 - 4;
        }
        for (int warm = 0; warm < 2000; warm++) sink += run(f, x, y);
        double[] perCall = new double[BATCHES];
        for (int b = 0; b < BATCHES; b++) {
            long start = System.nanoTime();
            sink += run(f, x, y);
            perCall[b] = (System.nanoTime() - start) / (double) INPUTS;
        }
        java.util.Arrays.sort(perCall);
        System.out.printf(java.util.Locale.ROOT, "{\"function\":\"%s\",\"variant\":\"hotspot\",\"median_ns\":%.3f,\"p99_ns\":%.3f}%n",
            f, perCall[BATCHES / 2], perCall[BATCHES * 99 / 100]);
    }
}
