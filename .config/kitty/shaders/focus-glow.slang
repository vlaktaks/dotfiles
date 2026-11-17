public float4
fragment_main(float4 color, KittyCustomShaderData d) {
    float t = d.animation_progress;
    if (t <= 0.0 || t >= 1.0) {
        return color;
    }

    float pulse = (1.0 - t) * (1.0 - t);
    float3 cyan = float3(0.173, 0.561, 0.620); // restrained cyan accent
    float strength = 0.03 * pulse;
    float3 mixed = lerp(color.rgb, cyan, strength);
    return float4(mixed, color.a);
}
