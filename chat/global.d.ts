declare const process: {
  env: Record<string, any>;
};

declare interface IChatMessage {
  id: string;
  username: string;
  avatar: string;
  text: string;
  text_html: string;
  time: number;
  quotes: null | string;
}
