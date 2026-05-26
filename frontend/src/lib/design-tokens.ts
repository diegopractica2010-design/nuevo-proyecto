import type { Transition } from "framer-motion";

export const colors = {
  primary: "#0a7c5c",
} as const;

export const transition = {
  hover: { duration: 0.2, ease: "easeOut" } satisfies Transition,
  page: { duration: 0.3, ease: "easeOut" } satisfies Transition,
  cardSpring: (index: number): Transition => ({
    type: "spring",
    duration: 0.4,
    delay: Math.min(index * 0.04, 0.32),
  }),
} as const;

export const cardEntrance = (index: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: transition.cardSpring(index),
});
