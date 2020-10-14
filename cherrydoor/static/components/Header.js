const HeaderTemplate = `
<header>
<img class="logo" src="/static/images/logo/logo.svg">
<h1 class="page-title">{{ pagename }}</h1>
<navbar></navbar>
</header>
`;

const Header = {
	data() {
		return {};
	},
	props: { pagename: String },
	template: HeaderTemplate,
};

export default Header;
