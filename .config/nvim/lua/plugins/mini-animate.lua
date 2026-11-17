return {
  "nvim-mini/mini.animate",
  event = "VeryLazy",
  opts = function()
    local animate = require("mini.animate")

    return {
      cursor = {
        enable = true,
        -- Keep cursor motion responsive and subtle.
        timing = animate.gen_timing.linear({ duration = 120, unit = "total" }),
        path = animate.gen_path.line(),
      },
      scroll = {
        enable = true,
        timing = animate.gen_timing.linear({ duration = 120, unit = "total" }),
        subscroll = animate.gen_subscroll.equal({ max_output_steps = 30 }),
      },
      resize = {
        enable = true,
        timing = animate.gen_timing.linear({ duration = 120, unit = "total" }),
        subresize = animate.gen_subresize.equal(),
      },
      open = {
        enable = true,
        timing = animate.gen_timing.linear({ duration = 150, unit = "total" }),
        winconfig = animate.gen_winconfig.static({ title = " " }),
        winblend = animate.gen_winblend.linear({ from = 80, to = 100 }),
      },
      close = {
        enable = true,
        timing = animate.gen_timing.linear({ duration = 150, unit = "total" }),
        winconfig = animate.gen_winconfig.static({ title = " " }),
        winblend = animate.gen_winblend.linear({ from = 80, to = 100 }),
      },
    }
  end,
}
