return {
  "nvim-mini/mini.animate",
  event = "VeryLazy",
  opts = {
    cursor = {
      enable = true,
      -- Keep cursor motion responsive and subtle.
      timing = require("mini.animate").gen_timing.linear({ duration = 120, unit = "total" }),
      path = require("mini.animate").gen_path.line({ predicate = function() return true end }),
    },
    scroll = {
      enable = true,
      timing = require("mini.animate").gen_timing.linear({ duration = 120, unit = "total" }),
      subscroll = require("mini.animate").gen_subscroll.equal({ max_output_steps = 30 }),
    },
    resize = {
      enable = true,
      timing = require("mini.animate").gen_timing.linear({ duration = 120, unit = "total" }),
      subresize = require("mini.animate").gen_subresize.equal(),
    },
    open = {
      enable = true,
      timing = require("mini.animate").gen_timing.linear({ duration = 150, unit = "total" }),
      winconfig = require("mini.animate").gen_winconfig.static({ title = " " }),
      winblend = require("mini.animate").gen_winblend.linear({ from = 80, to = 100 }),
    },
    close = {
      enable = true,
      timing = require("mini.animate").gen_timing.linear({ duration = 150, unit = "total" }),
      winconfig = require("mini.animate").gen_winconfig.static({ title = " " }),
      winblend = require("mini.animate").gen_winblend.linear({ from = 80, to = 100 }),
    },
  },
}
