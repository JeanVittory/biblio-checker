import pino from "pino";

const isServer = typeof window === "undefined";
const isDev = process.env.NODE_ENV === "development";

const logger = pino({
  level: isDev ? "debug" : "info",
  ...(isServer
    ? {
        ...(isDev && {
          transport: {
            target: "pino-pretty",
            options: { colorize: true },
          },
        }),
      }
    : {
        browser: {
          asObject: false,
        },
      }),
});

export default logger;
