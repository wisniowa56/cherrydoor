const HamburgerTemplate = `
<div class="menu-icon hover-target">
	<span class="menu-icon__line menu-icon__line-left"></span>
	<span class="menu-icon__line menu-icon__line-center"></span>
	<span class="menu-icon__line menu-icon__line_last menu-icon__line-right"></span>
</div>
`;

const HamburgerMenu = {
	data() {
		return {};
	},
	template: HamburgerTemplate,
};

export default HamburgerMenu;
