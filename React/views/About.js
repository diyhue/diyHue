import {
  FaGithub,
  FaTwitter,
  FaGlobeEurope,
  FaSlack
} from "react-icons/fa";
import kofi from "../static/images/kofi.svg";

const About = () => {
  return (
    <div className="inner">
      <div className="contentContainer">
        <div className="headline">About</div>
        <div className="form-control">
            <label>Debug information: (Copy and paste in Github issue)</label> 
            <textarea
              readOnly
              type="text"
              placeholder="bridgeid"
              value="Hue-Emulator Version: %Version%"
            />
          </div>
        <div className="supportsection">
          <p>Supported Devices:</p>
          <a href="https://diyhue.readthedocs.io/en/latest/">Link</a>
        </div>
        <div className="supportsection">
          <p>Support:</p>
          <a href="https://github.com/diyhue/diyhue"><FaGithub /></a>
          <a href="https://slackinvite.squishedmooo.com/"><FaSlack /></a>
        </div>
        <div className="supportsection">
          <p>License:</p>
          <p>ABC</p>
        </div>
        <div className="coffee">
          <p>Buy me a Coffee:</p>
          <a href="https://ko-fi.com/diyhue"><img src={kofi} alt="kofi" /></a>
        </div>
      </div>

      <div className="creditGrid">

        <div className="contactCard">
          <div className="name">Marius</div>
          <div className="position">Main Developer & Mastermind of DiyHue</div>
          <div className="about">Developing and maintaining basically everything. Thousands of hours spent for reverse engineering, bug fixing and trying to implement every possible feature in his project.</div>
          <div className="iconbox">
            <a href="https://github.com/mariusmotea"><FaGithub /></a>
          </div>
        </div>

        <div className="contactCard">
          <div className="name">cheesemarathon</div>
          <div className="position">Github & CI/CD Wizard</div>
          <div className="about">Created and maintaining the Github repository, Docker images and Github actions.</div>
          <div className="iconbox">
            <a href="https://github.com/cheesemarathon"><FaGithub /></a>
          </div>
        </div>

        <div className="contactCard">
          <div className="name">Mevel</div>
          <div className="position">Maintainer & Support </div>
          <div className="about">Maintaining the website, taking care of the community and running Slack are only a small portion of his efforts he invests into the project.</div>
          <div className="iconbox">
            <a href="https://github.com/Mevel"><FaGithub /></a>
          </div>
        </div>

        <div className="contactCard">
          <div className="name">David</div>
          <div className="position">Designer</div>
          <div className="about">Designed and frontend developed the user interface and user experience. Design and producing music (<a href="https://spaceflightmemories.com">Spaceflight Memories Music</a>) is, what his life is all about.</div>
          <div className="iconbox">
            <a href="https://github.com/fisico"><FaGithub /></a>
            <a href="https://twitter.com/sfmdavid"><FaTwitter /></a>
            <a href="https://spaceflightmemories.com"><FaGlobeEurope /></a>
          </div>
        </div>

        <div className="contactCard">
          <div className="name">Phil</div>
          <div className="position">React consultant</div>
          <div className="about">A very special thank you to Phil for consulting us with everything React related.</div>
          <div className="iconbox">
            <a href="https://github.com/philharmonie"><FaGithub /></a>
          </div>
        </div>

        <div className="contactCard">
          <div className="name">Thank you!</div>
          <div className="position">A big thank you to everyone contributing to this project:</div>
          contributor, contributor, contributor, contributor, contributor, contributor, contributor, contributor, contributor, contributor, contributor, contributor,
        </div>

      </div>
      </div>
      
  );
};

export default About;
