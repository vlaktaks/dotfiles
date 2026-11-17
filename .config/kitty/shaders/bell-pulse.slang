public float4
fragment_main(float4 color, KittyCustomShaderData d) {
    // Subtle Rundfunk-inspired gold pulse on terminal bell.
    float t = d.animation_progress;
    if (t <= 0.0 || t >= 1.0) {
        return color;
    }

    // Smooth in/out envelope.
    float pulse = smoothstep(0.0, 0.25, t) * (1.0 - smoothstep(0.25, 1.0, t));

    float3 gold = float3(0.667, 0.514, 0.102); // ~#D6B45A in linear-ish RGB
    float strength = 0.045 * pulse;
    float3 mixed = lerp(color.rgb, gold, strength);
    return float4(mixed, color.a);
}
