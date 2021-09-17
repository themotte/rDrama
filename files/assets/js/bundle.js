
(function(l, r) { if (!l || l.getElementById('livereloadscript')) return; r = l.createElement('script'); r.async = 1; r.src = '//' + (self.location.host || 'localhost').split(':')[0] + ':35729/livereload.js?snipver=1'; r.id = 'livereloadscript'; l.getElementsByTagName('head')[0].appendChild(r) })(self.document);
(function () {
    'use strict';

    function noop() { }
    function add_location(element, file, line, column, char) {
        element.__svelte_meta = {
            loc: { file, line, column, char }
        };
    }
    function run(fn) {
        return fn();
    }
    function blank_object() {
        return Object.create(null);
    }
    function run_all(fns) {
        fns.forEach(run);
    }
    function is_function(thing) {
        return typeof thing === 'function';
    }
    function safe_not_equal(a, b) {
        return a != a ? b == b : a !== b || ((a && typeof a === 'object') || typeof a === 'function');
    }
    function is_empty(obj) {
        return Object.keys(obj).length === 0;
    }
    function append(target, node) {
        target.appendChild(node);
    }
    function insert(target, node, anchor) {
        target.insertBefore(node, anchor || null);
    }
    function detach(node) {
        node.parentNode.removeChild(node);
    }
    function destroy_each(iterations, detaching) {
        for (let i = 0; i < iterations.length; i += 1) {
            if (iterations[i])
                iterations[i].d(detaching);
        }
    }
    function element(name) {
        return document.createElement(name);
    }
    function text(data) {
        return document.createTextNode(data);
    }
    function space() {
        return text(' ');
    }
    function empty() {
        return text('');
    }
    function listen(node, event, handler, options) {
        node.addEventListener(event, handler, options);
        return () => node.removeEventListener(event, handler, options);
    }
    function attr(node, attribute, value) {
        if (value == null)
            node.removeAttribute(attribute);
        else if (node.getAttribute(attribute) !== value)
            node.setAttribute(attribute, value);
    }
    function children(element) {
        return Array.from(element.childNodes);
    }
    function set_input_value(input, value) {
        input.value = value == null ? '' : value;
    }
    function set_style(node, key, value, important) {
        node.style.setProperty(key, value, important ? 'important' : '');
    }
    function toggle_class(element, name, toggle) {
        element.classList[toggle ? 'add' : 'remove'](name);
    }
    function custom_event(type, detail, bubbles = false) {
        const e = document.createEvent('CustomEvent');
        e.initCustomEvent(type, bubbles, false, detail);
        return e;
    }

    let current_component;
    function set_current_component(component) {
        current_component = component;
    }

    const dirty_components = [];
    const binding_callbacks = [];
    const render_callbacks = [];
    const flush_callbacks = [];
    const resolved_promise = Promise.resolve();
    let update_scheduled = false;
    function schedule_update() {
        if (!update_scheduled) {
            update_scheduled = true;
            resolved_promise.then(flush);
        }
    }
    function add_render_callback(fn) {
        render_callbacks.push(fn);
    }
    let flushing = false;
    const seen_callbacks = new Set();
    function flush() {
        if (flushing)
            return;
        flushing = true;
        do {
            // first, call beforeUpdate functions
            // and update components
            for (let i = 0; i < dirty_components.length; i += 1) {
                const component = dirty_components[i];
                set_current_component(component);
                update(component.$$);
            }
            set_current_component(null);
            dirty_components.length = 0;
            while (binding_callbacks.length)
                binding_callbacks.pop()();
            // then, once components are updated, call
            // afterUpdate functions. This may cause
            // subsequent updates...
            for (let i = 0; i < render_callbacks.length; i += 1) {
                const callback = render_callbacks[i];
                if (!seen_callbacks.has(callback)) {
                    // ...so guard against infinite loops
                    seen_callbacks.add(callback);
                    callback();
                }
            }
            render_callbacks.length = 0;
        } while (dirty_components.length);
        while (flush_callbacks.length) {
            flush_callbacks.pop()();
        }
        update_scheduled = false;
        flushing = false;
        seen_callbacks.clear();
    }
    function update($$) {
        if ($$.fragment !== null) {
            $$.update();
            run_all($$.before_update);
            const dirty = $$.dirty;
            $$.dirty = [-1];
            $$.fragment && $$.fragment.p($$.ctx, dirty);
            $$.after_update.forEach(add_render_callback);
        }
    }
    const outroing = new Set();
    function transition_in(block, local) {
        if (block && block.i) {
            outroing.delete(block);
            block.i(local);
        }
    }
    function mount_component(component, target, anchor, customElement) {
        const { fragment, on_mount, on_destroy, after_update } = component.$$;
        fragment && fragment.m(target, anchor);
        if (!customElement) {
            // onMount happens before the initial afterUpdate
            add_render_callback(() => {
                const new_on_destroy = on_mount.map(run).filter(is_function);
                if (on_destroy) {
                    on_destroy.push(...new_on_destroy);
                }
                else {
                    // Edge case - component was destroyed immediately,
                    // most likely as a result of a binding initialising
                    run_all(new_on_destroy);
                }
                component.$$.on_mount = [];
            });
        }
        after_update.forEach(add_render_callback);
    }
    function destroy_component(component, detaching) {
        const $$ = component.$$;
        if ($$.fragment !== null) {
            run_all($$.on_destroy);
            $$.fragment && $$.fragment.d(detaching);
            // TODO null out other refs, including component.$$ (but need to
            // preserve final state?)
            $$.on_destroy = $$.fragment = null;
            $$.ctx = [];
        }
    }
    function make_dirty(component, i) {
        if (component.$$.dirty[0] === -1) {
            dirty_components.push(component);
            schedule_update();
            component.$$.dirty.fill(0);
        }
        component.$$.dirty[(i / 31) | 0] |= (1 << (i % 31));
    }
    function init(component, options, instance, create_fragment, not_equal, props, append_styles, dirty = [-1]) {
        const parent_component = current_component;
        set_current_component(component);
        const $$ = component.$$ = {
            fragment: null,
            ctx: null,
            // state
            props,
            update: noop,
            not_equal,
            bound: blank_object(),
            // lifecycle
            on_mount: [],
            on_destroy: [],
            on_disconnect: [],
            before_update: [],
            after_update: [],
            context: new Map(parent_component ? parent_component.$$.context : options.context || []),
            // everything else
            callbacks: blank_object(),
            dirty,
            skip_bound: false,
            root: options.target || parent_component.$$.root
        };
        append_styles && append_styles($$.root);
        let ready = false;
        $$.ctx = instance
            ? instance(component, options.props || {}, (i, ret, ...rest) => {
                const value = rest.length ? rest[0] : ret;
                if ($$.ctx && not_equal($$.ctx[i], $$.ctx[i] = value)) {
                    if (!$$.skip_bound && $$.bound[i])
                        $$.bound[i](value);
                    if (ready)
                        make_dirty(component, i);
                }
                return ret;
            })
            : [];
        $$.update();
        ready = true;
        run_all($$.before_update);
        // `false` as a special case of no DOM component
        $$.fragment = create_fragment ? create_fragment($$.ctx) : false;
        if (options.target) {
            if (options.hydrate) {
                const nodes = children(options.target);
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                $$.fragment && $$.fragment.l(nodes);
                nodes.forEach(detach);
            }
            else {
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                $$.fragment && $$.fragment.c();
            }
            if (options.intro)
                transition_in(component.$$.fragment);
            mount_component(component, options.target, options.anchor, options.customElement);
            flush();
        }
        set_current_component(parent_component);
    }
    /**
     * Base class for Svelte components. Used when dev=false.
     */
    class SvelteComponent {
        $destroy() {
            destroy_component(this, 1);
            this.$destroy = noop;
        }
        $on(type, callback) {
            const callbacks = (this.$$.callbacks[type] || (this.$$.callbacks[type] = []));
            callbacks.push(callback);
            return () => {
                const index = callbacks.indexOf(callback);
                if (index !== -1)
                    callbacks.splice(index, 1);
            };
        }
        $set($$props) {
            if (this.$$set && !is_empty($$props)) {
                this.$$.skip_bound = true;
                this.$$set($$props);
                this.$$.skip_bound = false;
            }
        }
    }

    function dispatch_dev(type, detail) {
        document.dispatchEvent(custom_event(type, Object.assign({ version: '3.42.6' }, detail), true));
    }
    function append_dev(target, node) {
        dispatch_dev('SvelteDOMInsert', { target, node });
        append(target, node);
    }
    function insert_dev(target, node, anchor) {
        dispatch_dev('SvelteDOMInsert', { target, node, anchor });
        insert(target, node, anchor);
    }
    function detach_dev(node) {
        dispatch_dev('SvelteDOMRemove', { node });
        detach(node);
    }
    function listen_dev(node, event, handler, options, has_prevent_default, has_stop_propagation) {
        const modifiers = options === true ? ['capture'] : options ? Array.from(Object.keys(options)) : [];
        if (has_prevent_default)
            modifiers.push('preventDefault');
        if (has_stop_propagation)
            modifiers.push('stopPropagation');
        dispatch_dev('SvelteDOMAddEventListener', { node, event, handler, modifiers });
        const dispose = listen(node, event, handler, options);
        return () => {
            dispatch_dev('SvelteDOMRemoveEventListener', { node, event, handler, modifiers });
            dispose();
        };
    }
    function attr_dev(node, attribute, value) {
        attr(node, attribute, value);
        if (value == null)
            dispatch_dev('SvelteDOMRemoveAttribute', { node, attribute });
        else
            dispatch_dev('SvelteDOMSetAttribute', { node, attribute, value });
    }
    function set_data_dev(text, data) {
        data = '' + data;
        if (text.wholeText === data)
            return;
        dispatch_dev('SvelteDOMSetData', { node: text, data });
        text.data = data;
    }
    function validate_each_argument(arg) {
        if (typeof arg !== 'string' && !(arg && typeof arg === 'object' && 'length' in arg)) {
            let msg = '{#each} only iterates over array-like objects.';
            if (typeof Symbol === 'function' && arg && Symbol.iterator in arg) {
                msg += ' You can use a spread to convert this iterable into an array.';
            }
            throw new Error(msg);
        }
    }
    function validate_slots(name, slot, keys) {
        for (const slot_key of Object.keys(slot)) {
            if (!~keys.indexOf(slot_key)) {
                console.warn(`<${name}> received an unexpected slot "${slot_key}".`);
            }
        }
    }
    /**
     * Base class for Svelte components with some minor dev-enhancements. Used when dev=true.
     */
    class SvelteComponentDev extends SvelteComponent {
        constructor(options) {
            if (!options || (!options.target && !options.$$inline)) {
                throw new Error("'target' is a required option");
            }
            super();
        }
        $destroy() {
            super.$destroy();
            this.$destroy = () => {
                console.warn('Component was already destroyed'); // eslint-disable-line no-console
            };
        }
        $capture_state() { }
        $inject_state() { }
    }

    /* src\App.svelte generated by Svelte v3.42.6 */

    const file = "src\\App.svelte";

    function get_each_context(ctx, list, i) {
    	const child_ctx = ctx.slice();
    	child_ctx[7] = list[i];
    	child_ctx[9] = i;
    	return child_ctx;
    }

    // (54:7) {#if award.owned < 1}
    function create_if_block_2(ctx) {
    	let input;
    	let t0;
    	let label;
    	let i;
    	let i_class_value;
    	let br;
    	let t1;
    	let span1;
    	let t2_value = /*award*/ ctx[7].title + "";
    	let t2;
    	let t3;
    	let span0;
    	let t4_value = /*award*/ ctx[7].owned + "";
    	let t4;
    	let t5;
    	let t6;
    	let mounted;
    	let dispose;

    	const block = {
    		c: function create() {
    			input = element("input");
    			t0 = space();
    			label = element("label");
    			i = element("i");
    			br = element("br");
    			t1 = space();
    			span1 = element("span");
    			t2 = text(t2_value);
    			t3 = text("/span>\r\n\t\t\t\t\t\t\t\t\t");
    			span0 = element("span");
    			t4 = text(t4_value);
    			t5 = text(" owned");
    			t6 = space();
    			attr_dev(input, "type", "radio");
    			attr_dev(input, "id", /*index*/ ctx[9]);
    			attr_dev(input, "class", "svelte-13ovg7j");
    			toggle_class(input, "disabled", /*award*/ ctx[7].owned < 1);
    			add_location(input, file, 54, 8, 1321);
    			attr_dev(i, "class", i_class_value = "" + (/*award*/ ctx[7].icon + " " + /*award*/ ctx[7].color + " svelte-13ovg7j"));
    			add_location(i, file, 56, 9, 1499);
    			add_location(br, file, 56, 51, 1541);
    			attr_dev(span0, "class", "text-muted");
    			add_location(span0, file, 58, 9, 1659);
    			attr_dev(span1, "class", "d-block pt-2");
    			set_style(span1, "font-weight", "bold");
    			set_style(span1, "font-size", "14px");
    			add_location(span1, file, 57, 9, 1558);
    			attr_dev(label, "class", "card svelte-13ovg7j");
    			attr_dev(label, "for", /*index*/ ctx[9]);
    			toggle_class(label, "disabled", /*award*/ ctx[7].owned < 1);
    			add_location(label, file, 55, 8, 1419);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, input, anchor);
    			set_input_value(input, /*picked*/ ctx[1]);
    			insert_dev(target, t0, anchor);
    			insert_dev(target, label, anchor);
    			append_dev(label, i);
    			append_dev(label, br);
    			append_dev(label, t1);
    			append_dev(label, span1);
    			append_dev(span1, t2);
    			append_dev(span1, t3);
    			append_dev(span1, span0);
    			append_dev(span0, t4);
    			append_dev(span0, t5);
    			append_dev(span1, t6);

    			if (!mounted) {
    				dispose = listen_dev(input, "change", /*input_change_handler*/ ctx[5]);
    				mounted = true;
    			}
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*picked*/ 2) {
    				set_input_value(input, /*picked*/ ctx[1]);
    			}

    			if (dirty & /*awards*/ 4) {
    				toggle_class(input, "disabled", /*award*/ ctx[7].owned < 1);
    			}

    			if (dirty & /*awards*/ 4 && i_class_value !== (i_class_value = "" + (/*award*/ ctx[7].icon + " " + /*award*/ ctx[7].color + " svelte-13ovg7j"))) {
    				attr_dev(i, "class", i_class_value);
    			}

    			if (dirty & /*awards*/ 4 && t2_value !== (t2_value = /*award*/ ctx[7].title + "")) set_data_dev(t2, t2_value);
    			if (dirty & /*awards*/ 4 && t4_value !== (t4_value = /*award*/ ctx[7].owned + "")) set_data_dev(t4, t4_value);

    			if (dirty & /*awards*/ 4) {
    				toggle_class(label, "disabled", /*award*/ ctx[7].owned < 1);
    			}
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(input);
    			if (detaching) detach_dev(t0);
    			if (detaching) detach_dev(label);
    			mounted = false;
    			dispose();
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_if_block_2.name,
    		type: "if",
    		source: "(54:7) {#if award.owned < 1}",
    		ctx
    	});

    	return block;
    }

    // (53:6) {#each awards as award, index}
    function create_each_block(ctx) {
    	let if_block_anchor;
    	let if_block = /*award*/ ctx[7].owned < 1 && create_if_block_2(ctx);

    	const block = {
    		c: function create() {
    			if (if_block) if_block.c();
    			if_block_anchor = empty();
    		},
    		m: function mount(target, anchor) {
    			if (if_block) if_block.m(target, anchor);
    			insert_dev(target, if_block_anchor, anchor);
    		},
    		p: function update(ctx, dirty) {
    			if (/*award*/ ctx[7].owned < 1) {
    				if (if_block) {
    					if_block.p(ctx, dirty);
    				} else {
    					if_block = create_if_block_2(ctx);
    					if_block.c();
    					if_block.m(if_block_anchor.parentNode, if_block_anchor);
    				}
    			} else if (if_block) {
    				if_block.d(1);
    				if_block = null;
    			}
    		},
    		d: function destroy(detaching) {
    			if (if_block) if_block.d(detaching);
    			if (detaching) detach_dev(if_block_anchor);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_each_block.name,
    		type: "each",
    		source: "(53:6) {#each awards as award, index}",
    		ctx
    	});

    	return block;
    }

    // (65:5) {#if picked != null}
    function create_if_block_1(ctx) {
    	let div2;
    	let div1;
    	let i;
    	let t0;
    	let div0;
    	let strong;
    	let br;
    	let t3;
    	let span;
    	let t5;
    	let label;
    	let t7;
    	let textarea;
    	let mounted;
    	let dispose;

    	const block = {
    		c: function create() {
    			div2 = element("div");
    			div1 = element("div");
    			i = element("i");
    			t0 = space();
    			div0 = element("div");
    			strong = element("strong");
    			strong.textContent = `${/*pickedAward*/ ctx[4].title} Award`;
    			br = element("br");
    			t3 = space();
    			span = element("span");
    			span.textContent = `${/*pickedAward*/ ctx[4].description}`;
    			t5 = space();
    			label = element("label");
    			label.textContent = "Note (optional):";
    			t7 = space();
    			textarea = element("textarea");
    			set_style(i, "font-size", "35px");
    			attr_dev(i, "class", "" + (/*pickedAward*/ ctx[4].icon + " " + /*pickedAward*/ ctx[4].color + " svelte-13ovg7j"));
    			add_location(i, file, 67, 8, 1859);
    			add_location(strong, file, 69, 9, 1991);
    			add_location(br, file, 69, 51, 2033);
    			attr_dev(span, "class", "text-muted");
    			add_location(span, file, 70, 9, 2050);
    			set_style(div0, "margin-left", "15px");
    			add_location(div0, file, 68, 8, 1948);
    			attr_dev(div1, "class", "award-desc p-3 svelte-13ovg7j");
    			add_location(div1, file, 66, 7, 1821);
    			attr_dev(label, "for", "note");
    			attr_dev(label, "class", "pt-4");
    			add_location(label, file, 73, 7, 2147);
    			attr_dev(textarea, "id", "note");
    			attr_dev(textarea, "name", "note");
    			attr_dev(textarea, "class", "form-control");
    			attr_dev(textarea, "placeholder", "Note to include in award notification");
    			add_location(textarea, file, 74, 7, 2211);
    			add_location(div2, file, 65, 6, 1807);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div2, anchor);
    			append_dev(div2, div1);
    			append_dev(div1, i);
    			append_dev(div1, t0);
    			append_dev(div1, div0);
    			append_dev(div0, strong);
    			append_dev(div0, br);
    			append_dev(div0, t3);
    			append_dev(div0, span);
    			append_dev(div2, t5);
    			append_dev(div2, label);
    			append_dev(div2, t7);
    			append_dev(div2, textarea);
    			set_input_value(textarea, /*note*/ ctx[0]);

    			if (!mounted) {
    				dispose = listen_dev(textarea, "input", /*textarea_input_handler*/ ctx[6]);
    				mounted = true;
    			}
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*note*/ 1) {
    				set_input_value(textarea, /*note*/ ctx[0]);
    			}
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div2);
    			mounted = false;
    			dispose();
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_if_block_1.name,
    		type: "if",
    		source: "(65:5) {#if picked != null}",
    		ctx
    	});

    	return block;
    }

    // (87:3) {:else}
    function create_else_block(ctx) {
    	let button;
    	let mounted;
    	let dispose;

    	const block = {
    		c: function create() {
    			button = element("button");
    			button.textContent = "Give Award";
    			attr_dev(button, "type", "submit");
    			attr_dev(button, "class", "btn btn-link");
    			attr_dev(button, "id", "awardButton");
    			toggle_class(button, "disabled", /*pickedAward*/ ctx[4] === null);
    			add_location(button, file, 87, 4, 2743);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, button, anchor);

    			if (!mounted) {
    				dispose = listen_dev(button, "click", submit, false, false, false);
    				mounted = true;
    			}
    		},
    		p: noop,
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(button);
    			mounted = false;
    			dispose();
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_else_block.name,
    		type: "else",
    		source: "(87:3) {:else}",
    		ctx
    	});

    	return block;
    }

    // (82:3) {#if pending}
    function create_if_block(ctx) {
    	let button;
    	let span;
    	let t;

    	const block = {
    		c: function create() {
    			button = element("button");
    			span = element("span");
    			t = text("\r\n\t\t\t\t\tGifting...");
    			attr_dev(span, "class", "spinner-border spinner-border-sm");
    			attr_dev(span, "role", "status");
    			attr_dev(span, "aria-hidden", "true");
    			add_location(span, file, 83, 5, 2606);
    			attr_dev(button, "class", "btn btn-warning");
    			attr_dev(button, "type", "button");
    			button.disabled = true;
    			add_location(button, file, 82, 4, 2544);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, button, anchor);
    			append_dev(button, span);
    			append_dev(button, t);
    		},
    		p: noop,
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(button);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_if_block.name,
    		type: "if",
    		source: "(82:3) {#if pending}",
    		ctx
    	});

    	return block;
    }

    function create_fragment(ctx) {
    	let div6;
    	let input;
    	let t0;
    	let div5;
    	let div4;
    	let div0;
    	let h5;
    	let t2;
    	let button0;
    	let span;
    	let i;
    	let t3;
    	let div2;
    	let form;
    	let div1;
    	let t4;
    	let t5;
    	let div3;
    	let button1;
    	let t7;
    	let each_value = /*awards*/ ctx[2];
    	validate_each_argument(each_value);
    	let each_blocks = [];

    	for (let i = 0; i < each_value.length; i += 1) {
    		each_blocks[i] = create_each_block(get_each_context(ctx, each_value, i));
    	}

    	let if_block0 = /*picked*/ ctx[1] != null && create_if_block_1(ctx);

    	function select_block_type(ctx, dirty) {
    		if (/*pending*/ ctx[3]) return create_if_block;
    		return create_else_block;
    	}

    	let current_block_type = select_block_type(ctx);
    	let if_block1 = current_block_type(ctx);

    	const block = {
    		c: function create() {
    			div6 = element("div");
    			input = element("input");
    			t0 = space();
    			div5 = element("div");
    			div4 = element("div");
    			div0 = element("div");
    			h5 = element("h5");
    			h5.textContent = "Give Award";
    			t2 = space();
    			button0 = element("button");
    			span = element("span");
    			i = element("i");
    			t3 = space();
    			div2 = element("div");
    			form = element("form");
    			div1 = element("div");

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				each_blocks[i].c();
    			}

    			t4 = space();
    			if (if_block0) if_block0.c();
    			t5 = space();
    			div3 = element("div");
    			button1 = element("button");
    			button1.textContent = "Cancel";
    			t7 = space();
    			if_block1.c();
    			attr_dev(input, "type", "hidden");
    			attr_dev(input, "id", "awardTarget");
    			input.value = "";
    			add_location(input, file, 40, 0, 694);
    			attr_dev(h5, "class", "modal-title");
    			add_location(h5, file, 44, 4, 902);
    			attr_dev(i, "class", "far fa-times");
    			add_location(i, file, 46, 30, 1055);
    			attr_dev(span, "aria-hidden", "true");
    			add_location(span, file, 46, 5, 1030);
    			attr_dev(button0, "type", "button");
    			attr_dev(button0, "class", "close");
    			attr_dev(button0, "data-dismiss", "modal");
    			attr_dev(button0, "aria-label", "Close");
    			add_location(button0, file, 45, 4, 947);
    			attr_dev(div0, "class", "modal-header");
    			add_location(div0, file, 43, 3, 870);
    			attr_dev(div1, "class", "card-columns awards-wrapper svelte-13ovg7j");
    			add_location(div1, file, 51, 5, 1202);
    			attr_dev(form, "class", "pt-3 pb-0");
    			add_location(form, file, 50, 4, 1171);
    			attr_dev(div2, "id", "awardModalBody");
    			attr_dev(div2, "class", "modal-body");
    			add_location(div2, file, 49, 3, 1121);
    			attr_dev(button1, "type", "button");
    			attr_dev(button1, "class", "btn btn-link text-muted");
    			attr_dev(button1, "data-dismiss", "modal");
    			add_location(button1, file, 80, 3, 2430);
    			attr_dev(div3, "class", "modal-footer");
    			add_location(div3, file, 79, 2, 2399);
    			attr_dev(div4, "class", "modal-content");
    			add_location(div4, file, 42, 2, 838);
    			attr_dev(div5, "class", "modal-dialog modal-dialog-scrollable modal-dialog-centered");
    			attr_dev(div5, "role", "document");
    			add_location(div5, file, 41, 1, 746);
    			attr_dev(div6, "id", "svelte-app2");
    			add_location(div6, file, 39, 0, 670);
    		},
    		l: function claim(nodes) {
    			throw new Error("options.hydrate only works if the component was compiled with the `hydratable: true` option");
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div6, anchor);
    			append_dev(div6, input);
    			append_dev(div6, t0);
    			append_dev(div6, div5);
    			append_dev(div5, div4);
    			append_dev(div4, div0);
    			append_dev(div0, h5);
    			append_dev(div0, t2);
    			append_dev(div0, button0);
    			append_dev(button0, span);
    			append_dev(span, i);
    			append_dev(div4, t3);
    			append_dev(div4, div2);
    			append_dev(div2, form);
    			append_dev(form, div1);

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				each_blocks[i].m(div1, null);
    			}

    			append_dev(form, t4);
    			if (if_block0) if_block0.m(form, null);
    			append_dev(div4, t5);
    			append_dev(div4, div3);
    			append_dev(div3, button1);
    			append_dev(div3, t7);
    			if_block1.m(div3, null);
    		},
    		p: function update(ctx, [dirty]) {
    			if (dirty & /*awards, picked*/ 6) {
    				each_value = /*awards*/ ctx[2];
    				validate_each_argument(each_value);
    				let i;

    				for (i = 0; i < each_value.length; i += 1) {
    					const child_ctx = get_each_context(ctx, each_value, i);

    					if (each_blocks[i]) {
    						each_blocks[i].p(child_ctx, dirty);
    					} else {
    						each_blocks[i] = create_each_block(child_ctx);
    						each_blocks[i].c();
    						each_blocks[i].m(div1, null);
    					}
    				}

    				for (; i < each_blocks.length; i += 1) {
    					each_blocks[i].d(1);
    				}

    				each_blocks.length = each_value.length;
    			}

    			if (/*picked*/ ctx[1] != null) {
    				if (if_block0) {
    					if_block0.p(ctx, dirty);
    				} else {
    					if_block0 = create_if_block_1(ctx);
    					if_block0.c();
    					if_block0.m(form, null);
    				}
    			} else if (if_block0) {
    				if_block0.d(1);
    				if_block0 = null;
    			}

    			if_block1.p(ctx, dirty);
    		},
    		i: noop,
    		o: noop,
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div6);
    			destroy_each(each_blocks, detaching);
    			if (if_block0) if_block0.d();
    			if_block1.d();
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_fragment.name,
    		type: "component",
    		source: "",
    		ctx
    	});

    	return block;
    }

    function submit() {
    	this.pending = true;
    	const target = document.getElementById("awardTarget").value;
    	const f = new FormData();
    	f.append("formkey", formkey());
    	f.append("kind", this.pickedAward.kind || "");
    	f.append("note", this.note);
    	fetch(target, { method: "POST", body: f });
    	location.reload();
    }

    function instance($$self, $$props, $$invalidate) {
    	let { $$slots: slots = {}, $$scope } = $$props;
    	validate_slots('App', slots, []);
    	let pending = false;
    	let note = "";
    	let picked = null;
    	let awards = {};

    	fetch('/awards').then(response => response.json()).then(json => {
    		$$invalidate(2, awards = json);
    	});

    	function pickedAward() {
    		if (picked !== null) {
    			return awards[picked];
    		} else {
    			return null;
    		}
    	}

    	const writable_props = [];

    	Object.keys($$props).forEach(key => {
    		if (!~writable_props.indexOf(key) && key.slice(0, 2) !== '$$' && key !== 'slot') console.warn(`<App> was created with unknown prop '${key}'`);
    	});

    	function input_change_handler() {
    		picked = this.value;
    		$$invalidate(1, picked);
    	}

    	function textarea_input_handler() {
    		note = this.value;
    		$$invalidate(0, note);
    	}

    	$$self.$capture_state = () => ({
    		pending,
    		note,
    		picked,
    		awards,
    		pickedAward,
    		submit
    	});

    	$$self.$inject_state = $$props => {
    		if ('pending' in $$props) $$invalidate(3, pending = $$props.pending);
    		if ('note' in $$props) $$invalidate(0, note = $$props.note);
    		if ('picked' in $$props) $$invalidate(1, picked = $$props.picked);
    		if ('awards' in $$props) $$invalidate(2, awards = $$props.awards);
    	};

    	if ($$props && "$$inject" in $$props) {
    		$$self.$inject_state($$props.$$inject);
    	}

    	return [
    		note,
    		picked,
    		awards,
    		pending,
    		pickedAward,
    		input_change_handler,
    		textarea_input_handler
    	];
    }

    class App extends SvelteComponentDev {
    	constructor(options) {
    		super(options);
    		init(this, options, instance, create_fragment, safe_not_equal, {});

    		dispatch_dev("SvelteRegisterComponent", {
    			component: this,
    			tagName: "App",
    			options,
    			id: create_fragment.name
    		});
    	}
    }

    new App({
    	target: document.querySelector('#awardModal')
    });

}());
//# sourceMappingURL=bundle.js.map
