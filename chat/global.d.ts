declare const process: {
  env: Record<string, any>;
};

declare interface IChatMessage {
  id: string;
  username: string;
  user_id?: string;
  avatar: string;
  text: string;
  text_html: string;
  time: number;
  quotes: null | string;
  dm: boolean;
}
